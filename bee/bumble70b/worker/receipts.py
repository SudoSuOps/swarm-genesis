"""
Job Receipts & Merkle Proofs for Bumble70B Worker
Cryptographic proof of execution for SwarmLedger/SwarmEpoch.
"""

import json
import hashlib
import time
import subprocess
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class JobReceipt:
    """
    Immutable receipt for a completed job.
    Compatible with SwarmLedger and SwarmEpoch.
    """
    job_id: str
    worker_ens: str
    model: str
    input_hash: str
    output_hash: str
    report_hash: str
    inference_time_ms: int
    confidence_score: int
    k_samples: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    epoch: int = 0
    ipfs_cid: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def compute_hash(self) -> str:
        """Compute SHA256 hash of the receipt."""
        # Canonical JSON for deterministic hashing
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def sign(self, private_key_path: str) -> str:
        """
        Sign the receipt hash with ED25519 key.
        Returns the signature in SSH signature format.
        """
        receipt_hash = self.compute_hash()

        # Write hash to temp file
        temp_hash_file = Path(f"/tmp/receipt_{self.job_id}_hash.txt")
        temp_sig_file = Path(f"/tmp/receipt_{self.job_id}_hash.txt.sig")

        try:
            temp_hash_file.write_text(receipt_hash)

            # Sign with ssh-keygen
            result = subprocess.run(
                [
                    "ssh-keygen", "-Y", "sign",
                    "-f", private_key_path,
                    "-n", "swarm-receipt",
                    temp_hash_file
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Signing failed: {result.stderr}")

            signature = temp_sig_file.read_text()
            return signature

        finally:
            temp_hash_file.unlink(missing_ok=True)
            temp_sig_file.unlink(missing_ok=True)


@dataclass
class MerkleNode:
    """Node in a Merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    is_leaf: bool = False
    data: Optional[str] = None  # For leaf nodes, the original data


class MerkleTree:
    """
    Merkle tree for batching receipts.
    Enables efficient proof of inclusion for any receipt.
    """

    def __init__(self, leaves: list[str] = None):
        self.leaves: list[str] = leaves or []
        self.root: Optional[MerkleNode] = None
        self._nodes: dict[str, MerkleNode] = {}

        if self.leaves:
            self._build()

    def _hash_pair(self, left: str, right: str) -> str:
        """Hash two values together."""
        combined = left + right
        return hashlib.sha256(combined.encode()).hexdigest()

    def _build(self):
        """Build the Merkle tree from leaves."""
        if not self.leaves:
            return

        # Create leaf nodes
        nodes = []
        for data in self.leaves:
            leaf_hash = hashlib.sha256(data.encode()).hexdigest()
            node = MerkleNode(hash=leaf_hash, is_leaf=True, data=data)
            self._nodes[leaf_hash] = node
            nodes.append(node)

        # Pad with duplicate if odd number
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])

        # Build tree bottom-up
        while len(nodes) > 1:
            next_level = []

            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]

                parent_hash = self._hash_pair(left.hash, right.hash)
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                self._nodes[parent_hash] = parent
                next_level.append(parent)

            nodes = next_level

        self.root = nodes[0] if nodes else None

    def add_leaf(self, data: str):
        """Add a new leaf and rebuild tree."""
        self.leaves.append(data)
        self._build()

    @property
    def root_hash(self) -> Optional[str]:
        """Get the root hash."""
        return self.root.hash if self.root else None

    def get_proof(self, data: str) -> list[dict]:
        """
        Get Merkle proof for a leaf.
        Returns list of {hash, position} pairs.
        """
        if not self.root:
            return []

        leaf_hash = hashlib.sha256(data.encode()).hexdigest()

        if leaf_hash not in self._nodes:
            return []

        proof = []
        current_hash = leaf_hash

        # Walk up the tree collecting sibling hashes
        def find_path(node: MerkleNode, target_hash: str, path: list) -> bool:
            if node.hash == target_hash:
                return True

            if node.left and find_path(node.left, target_hash, path):
                if node.right:
                    path.append({"hash": node.right.hash, "position": "right"})
                return True

            if node.right and find_path(node.right, target_hash, path):
                if node.left:
                    path.append({"hash": node.left.hash, "position": "left"})
                return True

            return False

        find_path(self.root, leaf_hash, proof)
        return proof

    def verify_proof(self, data: str, proof: list[dict], root_hash: str) -> bool:
        """Verify a Merkle proof."""
        current_hash = hashlib.sha256(data.encode()).hexdigest()

        for step in proof:
            sibling_hash = step["hash"]
            position = step["position"]

            if position == "right":
                current_hash = self._hash_pair(current_hash, sibling_hash)
            else:
                current_hash = self._hash_pair(sibling_hash, current_hash)

        return current_hash == root_hash

    def to_dict(self) -> dict:
        """Serialize tree to dictionary."""
        return {
            "root_hash": self.root_hash,
            "leaf_count": len(self.leaves),
            "leaves": self.leaves,
        }


class ReceiptManager:
    """
    Manages job receipts and Merkle trees.
    Batches receipts and creates periodic proofs.
    """

    def __init__(
        self,
        worker_ens: str,
        receipts_dir: Path,
        private_key_path: str,
        batch_size: int = 100,
        epoch: int = 0,
    ):
        self.worker_ens = worker_ens
        self.receipts_dir = Path(receipts_dir)
        self.private_key_path = private_key_path
        self.batch_size = batch_size
        self.epoch = epoch

        self.receipts_dir.mkdir(parents=True, exist_ok=True)

        self._current_batch: list[JobReceipt] = []
        self._current_tree: Optional[MerkleTree] = None
        self._batch_count = 0

    def create_receipt(
        self,
        job_id: str,
        model: str,
        input_data: str,
        output_data: str,
        report_content: str,
        inference_time_ms: int,
        confidence_score: int,
        k_samples: int,
    ) -> JobReceipt:
        """Create a new job receipt."""
        receipt = JobReceipt(
            job_id=job_id,
            worker_ens=self.worker_ens,
            model=model,
            input_hash=hashlib.sha256(input_data.encode()).hexdigest(),
            output_hash=hashlib.sha256(output_data.encode()).hexdigest(),
            report_hash=hashlib.sha256(report_content.encode()).hexdigest(),
            inference_time_ms=inference_time_ms,
            confidence_score=confidence_score,
            k_samples=k_samples,
            epoch=self.epoch,
        )

        # Add to current batch
        self._current_batch.append(receipt)

        # Save individual receipt
        receipt_path = self.receipts_dir / f"{job_id}_receipt.json"
        receipt_path.write_text(receipt.to_json())

        # Check if batch is full
        if len(self._current_batch) >= self.batch_size:
            self._seal_batch()

        return receipt

    def _seal_batch(self):
        """Seal current batch with Merkle tree."""
        if not self._current_batch:
            return

        self._batch_count += 1
        batch_id = f"batch_{self.epoch}_{self._batch_count:06d}"

        # Build Merkle tree from receipt hashes
        receipt_hashes = [r.compute_hash() for r in self._current_batch]
        tree = MerkleTree(receipt_hashes)

        # Create batch manifest
        manifest = {
            "batch_id": batch_id,
            "epoch": self.epoch,
            "worker_ens": self.worker_ens,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "receipt_count": len(self._current_batch),
            "merkle_root": tree.root_hash,
            "receipts": [r.job_id for r in self._current_batch],
        }

        # Save batch manifest
        batch_dir = self.receipts_dir / "batches"
        batch_dir.mkdir(exist_ok=True)

        manifest_path = batch_dir / f"{batch_id}_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Sign the Merkle root
        try:
            root_hash_file = batch_dir / f"{batch_id}_root.txt"
            root_hash_file.write_text(tree.root_hash)

            result = subprocess.run(
                [
                    "ssh-keygen", "-Y", "sign",
                    "-f", self.private_key_path,
                    "-n", "swarm-merkle",
                    str(root_hash_file)
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                sig_path = Path(str(root_hash_file) + ".sig")
                if sig_path.exists():
                    # Move sig to batch dir
                    sig_path.rename(batch_dir / f"{batch_id}_root.sig")

        except Exception as e:
            print(f"[RECEIPT] Failed to sign batch: {e}")

        # Clear current batch
        self._current_batch = []
        self._current_tree = None

        print(f"[RECEIPT] Sealed batch {batch_id} with {manifest['receipt_count']} receipts")
        print(f"[RECEIPT] Merkle root: {tree.root_hash[:16]}...")

    def get_proof_for_job(self, job_id: str) -> Optional[dict]:
        """Get Merkle proof for a specific job."""
        receipt_path = self.receipts_dir / f"{job_id}_receipt.json"

        if not receipt_path.exists():
            return None

        receipt_data = json.loads(receipt_path.read_text())
        receipt = JobReceipt(**receipt_data)
        receipt_hash = receipt.compute_hash()

        # Find the batch containing this receipt
        batch_dir = self.receipts_dir / "batches"
        if not batch_dir.exists():
            return None

        for manifest_path in batch_dir.glob("*_manifest.json"):
            manifest = json.loads(manifest_path.read_text())

            if job_id in manifest["receipts"]:
                # Load the tree and get proof
                # For production, we'd store the full tree, but for now we reconstruct
                all_receipt_hashes = []
                for jid in manifest["receipts"]:
                    rpath = self.receipts_dir / f"{jid}_receipt.json"
                    if rpath.exists():
                        r = JobReceipt(**json.loads(rpath.read_text()))
                        all_receipt_hashes.append(r.compute_hash())

                tree = MerkleTree(all_receipt_hashes)
                proof = tree.get_proof(receipt_hash)

                return {
                    "job_id": job_id,
                    "receipt_hash": receipt_hash,
                    "merkle_root": manifest["merkle_root"],
                    "batch_id": manifest["batch_id"],
                    "proof": proof,
                }

        return None

    def flush(self):
        """Flush any remaining receipts to a batch."""
        if self._current_batch:
            self._seal_batch()
