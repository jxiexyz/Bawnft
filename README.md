# Bawnft 🦅

> **Autonomous NFT Portfolio & Element Market Valuation Bridge for Binance Agentic Wallet (BAW)**

`Bawnft` bridges autonomous Web3 AI agents operating on Binance Agentic Wallet (`baw`) with Element Market's OpenAPI. It automatically inspects minted or received NFT assets, validates live on-chain token balances, and fetches real-time floor prices and highest purchase offers (top bids).

---

## ⚡ Highlights

- **Agent-First Design:** Features native `--json` output formatted specifically for LLM toolchains and autonomous agent workflows.
- **BAW Integration:** Automatically discovers NFT contracts minted or received via Binance Agentic Wallet (`baw wallet tx-history` / `baw wallet address`).
- **On-Chain Balance Verification:** Cross-checks contract ownership using direct RPC calls (`balanceOf`) to filter out sold or transferred tokens.
- **Element Market Valuation:** Queries Element Market OpenAPI (`/orders/list`) for:
  - **Floor Price (`side=1`):** Lowest active listing price (native token + USD).
  - **Top Offer / Best Bid (`side=0`):** Highest active collection or token offer (instant exit liquidity).
- **Zero Hallucination:** Directly returns on-chain token metadata (`name()`, `symbol()`, `token_ids`) paired with verified orderbook hashes.

---

## 📦 Prerequisites

1. **Python 3.10+**
2. **Binance Agentic Wallet CLI (`baw`)** (Optional if providing `--wallet` manually):
   ```bash
   npm install -g @binance/agentic-wallet
   ```
3. **Element Market API Key** (Optional, but recommended for production rates):
   - Get your key from [Element.market developer portal](https://element.market).

---

## 🚀 Installation

```bash
git clone https://github.com/jxiexyz/Bawnft.git
cd Bawnft
pip install -r requirements.txt
chmod +x bawnft.py
```

### Configuration (Optional)
Copy `.env.example` to `.env` or set environment variables:
```bash
cp .env.example .env
export ELEMENT_API_KEY="your_api_key_here"
```
Or keep your configuration in `~/.config/element/config.json`:
```json
{
  "api_key": "your_api_key_here"
}
```

---

## 🛠️ Usage

### 1. Human-Readable CLI Table
Scans the current active BAW wallet on BSC:
```bash
python3 bawnft.py
```

**Example Output:**
```text
[*] Scanning BAW NFT holdings for: 0x94b4b4548Ad8D3f805928e8582DBD3C9d4152932
[*] Reading transaction history & on-chain balances...
[+] Discovered 35 NFT Collections | 62 Total Tokens Held

NFT Name                     | Qty  | Floor Price            | Top Offer              | Contract Address
-------------------------------------------------------------------------------------------------------------------
CZ ID (#873)                 | 1    | 0.014 BNB ($9.86)      | 0.000101 BNB ($0.07)   | 0xb3bc98fb678a99FA890F6242cB332D08feF3104b
UNBROKEN (#1269, #1267)      | 2    | 0.000899 BNB ($0.63)   | No Offer               | 0x6F3Ad88E3660EeAda7Ebe37543Cc3CE68F95d414
Panda Editions               | 10   | No Listing             | No Offer               | 0xb7053136F6B80517540501fC1bD4Fc56A9d84d84
ElonGai                      | 6    | No Listing             | No Offer               | 0x59F93bBBb14cE948Ee16b261a05Ad4A77711ECf1
Agent Racers (#596)          | 5    | No Listing             | No Offer               | 0x3601A439aF531Ce57603A81719707e0bd1ff5269
```

### 2. Machine-Readable Agent Mode (`--json`)
Designed for autonomous agent decision-making:
```bash
python3 bawnft.py --json
```

**Schema:**
```json
{
  "success": true,
  "wallet": "0x94b4b4548Ad8D3f805928e8582DBD3C9d4152932",
  "chain": "bsc",
  "total_collections": 35,
  "total_tokens_held": 62,
  "collections": [
    {
      "contract_address": "0xb3bc98fb678a99FA890F6242cB332D08feF3104b",
      "name": "CZ ID",
      "symbol": "CZID",
      "balance": 1,
      "token_ids": ["873"],
      "floor_price_base": 0.014,
      "floor_price_usd": 9.86,
      "top_offer_base": 0.000101,
      "top_offer_usd": 0.07,
      "element_url": "https://element.market/assets/bsc/0xb3bc98fb678a99FA890F6242cB332D08feF3104b"
    }
  ]
}
```

### 3. Specify Target Wallet & Scan Depth
```bash
python3 bawnft.py --wallet 0x94b4b4548Ad8D3f805928e8582DBD3C9d4152932 --depth 200
```

### 4. Custom Chain or RPC
```bash
python3 bawnft.py --chain bsc --rpc https://binance.llamarpc.com
```

---

## 🤖 Agentic Architecture & Execution Loop

For AI agents managing NFT treasuries or performing arbitrage:

```
┌────────────────────────────────┐
│   Binance Agentic Wallet CLI   │
│ (`baw wallet tx-history / addr`)│
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│       Bawnft Analyzer          │ ──▶ Query On-Chain ERC-721 State
│  (`bawnft.py --json`)          │ ──▶ Query Element Market Orderbook
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│      Action Execution          │
│ - Instant Sell (Fill Offer)    │ ──▶ Element encodeTradeDataByOrderId
│ - List on Floor (EIP-712 sign) │ ──▶ BAW `contract-call` / `sign-message`
└────────────────────────────────┘
```

---

## 🛡️ Security

- **Read-Only Inspection:** `Bawnft` performs read-only operations (RPC `eth_call` and public OpenAPI queries).
- **No Private Keys Stored:** Never handles private keys directly. Any subsequent trading executions are delegated to `baw` secure signing sessions.

---

## 📄 License
MIT © [jxiexyz](https://github.com/jxiexyz)
