# SwarmOrb Deployment Guide

## Prerequisites

- Node.js 18+
- Python 3.11+
- IPFS CLI (for IPFS deployment)
- Wrangler CLI (for Cloudflare deployment)

## Build

```bash
# Install dependencies
make install

# Build static site
make build
```

Output: `./dist/` directory containing static HTML/CSS/JS

## Deployment Options

### Option 1: IPFS (Recommended for swarmorb.eth)

1. **Install IPFS CLI**
   ```bash
   # macOS
   brew install ipfs

   # Linux
   wget https://dist.ipfs.tech/kubo/v0.24.0/kubo_v0.24.0_linux-amd64.tar.gz
   tar -xvzf kubo_v0.24.0_linux-amd64.tar.gz
   sudo ./kubo/install.sh
   ```

2. **Initialize IPFS** (first time only)
   ```bash
   ipfs init
   ipfs daemon &
   ```

3. **Add to IPFS**
   ```bash
   make build
   ipfs add -r --quieter dist
   ```

   Output will be the CID, e.g.: `QmXxx...`

4. **Pin to Pinning Service** (optional but recommended)
   ```bash
   # Using Pinata
   npx pinata upload dist

   # Using web3.storage
   npx w3 put dist
   ```

5. **Update ENS Content Hash**
   - Go to app.ens.domains
   - Select `swarmorb.eth`
   - Set Content Hash to: `ipfs://QmXxx...`
   - Confirm transaction

6. **Access via ENS**
   - https://swarmorb.eth.limo
   - https://swarmorb.eth.link

### Option 2: Cloudflare Pages

1. **Install Wrangler**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

2. **Create Project**
   ```bash
   wrangler pages project create swarmorb
   ```

3. **Deploy**
   ```bash
   make build
   wrangler pages deploy dist --project-name=swarmorb
   ```

4. **Custom Domain** (optional)
   - In Cloudflare Dashboard → Pages → swarmorb
   - Custom domains → Add `swarmorb.io`

### Option 3: Vercel

```bash
make build
npx vercel dist --prod
```

### Option 4: GitHub Pages

1. Push `dist/` to `gh-pages` branch
2. Enable GitHub Pages in repo settings
3. Access at: `https://sudosuops.github.io/swarmorb/`

## Updating Data

### For Development

1. Place epoch bundles in `sample_data/audit/epoch-XXX/`
2. Run indexer:
   ```bash
   make index
   ```
3. Rebuild:
   ```bash
   make build
   ```

### For Production

1. **Option A: Bundled Data**
   - Include epoch data in `dist/data/`
   - Redeploy entire site

2. **Option B: External Data URL**
   - Set `PUBLIC_DATA_URL` environment variable
   - Point to IPFS gateway or API endpoint
   - UI fetches data from external source

   ```bash
   PUBLIC_DATA_URL=https://gateway.pinata.cloud/ipfs/QmXxx npm run build
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PUBLIC_DATA_URL` | Base URL for data files | `/data` |

## Verification

After deployment, verify:

1. **Homepage loads**: Check live stats display
2. **Epochs list**: Navigate to /epochs
3. **Epoch detail**: Click into an epoch
4. **Verify page**: Run hash verification on an epoch
5. **ENS resolution**: Access via .eth.limo domain

## Troubleshooting

### CORS Issues

If fetching external data:
- Ensure CORS headers are set on data source
- Use IPFS gateway that supports CORS

### Missing Data

If UI shows "Loading...":
- Check browser console for fetch errors
- Verify data files exist in `dist/data/`
- Check `PUBLIC_DATA_URL` is correct

### IPFS Slow

- Use multiple gateways
- Pin to Pinata/web3.storage
- Consider Cloudflare IPFS gateway

## Updating swarmorb.eth

When deploying new version to IPFS:

1. Build and upload to IPFS
2. Get new CID
3. Update ENS content hash
4. Wait for DNS propagation (~5 min)
5. Clear browser cache and verify

## CI/CD

Example GitHub Action:

```yaml
name: Deploy to IPFS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install
        run: make install
      
      - name: Build
        run: make build
      
      - name: Deploy to IPFS
        uses: aquiladev/ipfs-action@v0.3.1
        with:
          path: ./dist
          service: pinata
          pinataKey: ${{ secrets.PINATA_KEY }}
          pinataSecret: ${{ secrets.PINATA_SECRET }}
```
