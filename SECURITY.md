# Security Policy

## Secrets
Never commit API keys, wallet secrets, or `.env` files.

## Reporting
Email the maintainers or open a private GitHub security advisory.
Do not post live keys or private keys in public issues.

## Scope
HelloAgents is pre-mainnet. Treat Sepolia and local keys as disposable.
Do not send mainnet funds until wallets + settlement are production-ready.
Testnet: Base Sepolia via Turnkey. Keep `TURNKEY_*` secrets server-side only (Fly secrets / `.env`).
