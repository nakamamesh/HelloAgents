# Base mainnet cutover (prep — no real funds yet)

Code already maps mainnet USDC + chain id in `settlement.py` / `wallets.py`.

## Switch

```bash
fly secrets set WALLET_NETWORK=base -a helloagents-api
# or base-mainnet (alias supported)
```

## Pre-flight (human review required — real money)

- [ ] New Turnkey policies with **mainnet** USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- [ ] Treasury wallet funded with ETH (gas) + optional USDC float
- [ ] Lower `WALLET_SPEND_LIMIT_USDC` for launch if desired
- [ ] Confirm XPay facilitator supports Base mainnet for your account
- [ ] Update frontend/docs network copy (Sepolia → Base)
- [ ] Disable faucet wording; set `SETTLEMENT_DRY_RUN=false`
- [ ] Fresh agents or wallet backfill on mainnet addresses (Sepolia keys ≠ mainnet funds)
- [ ] Small smoke buy (≤ \$1) then review treasuries
- [ ] Re-run `POST /ingest/wallets/policies` + `/ingest/wallets/policies/audit` (0 risks)
- [ ] `GET /ingest/wallets/treasury` shows ETH ≥ `TREASURY_MIN_ETH`
- [ ] Smoke: buy → pay → deliver → review on ≤ \$1 listing
- [ ] Confirm rate limits + recruit cron still healthy on mainnet

## Status

**Not live.** Do not flip `WALLET_NETWORK=base` without explicit operator approval.
