#!/usr/bin/env python3
"""
Bawnft - Binance Agentic Wallet (BAW) NFT Portfolio & Element Market Floor/Offer Scanner
Scans on-chain NFT holdings for an agentic wallet and queries Element Market OpenAPI
for real-time collection floor prices and top purchase offers.
"""

import os
import sys
import json
import argparse
import subprocess
import requests
from web3 import Web3

DEFAULT_RPC_MAP = {
    "bsc": os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org/"),
    "ethereum": os.environ.get("ETH_RPC", "https://eth.llamarpc.com"),
    "base": os.environ.get("BASE_RPC", "https://mainnet.base.org"),
    "polygon": os.environ.get("POLYGON_RPC", "https://polygon-rpc.com")
}

ERC721_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

def load_element_api_key(cli_key=None):
    if cli_key:
        return cli_key
    env_key = os.environ.get("ELEMENT_API_KEY")
    if env_key:
        return env_key
    
    # Check ~/.config/element/config.json
    cfg_path = os.path.expanduser("~/.config/element/config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("api_key")
                if key:
                    return key
        except Exception:
            pass
    return None

def resolve_baw_wallet(wallet_arg=None):
    if wallet_arg:
        return Web3.to_checksum_address(wallet_arg)
    
    # Attempt to resolve from `baw wallet address --json`
    try:
        res = subprocess.run(["baw", "wallet", "address", "--json"], capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        for entry in data.get("data", {}).get("addresses", []):
            if entry.get("chainName") in ["BSC", "Ethereum"]:
                addr = entry.get("address")
                if addr:
                    return Web3.to_checksum_address(addr)
    except Exception:
        pass
    
    print("[ERROR] No wallet address specified and could not auto-resolve from BAW CLI.", file=sys.stderr)
    print("Provide --wallet 0x... or ensure `baw` CLI is logged in.", file=sys.stderr)
    sys.exit(1)

def scan_baw_history_for_nfts(depth=100):
    """
    Scan transaction history from BAW CLI to identify NFT contract addresses received or minted.
    """
    contracts = {}
    try:
        res = subprocess.run(["baw", "wallet", "tx-history", "--size", str(depth), "--json"], capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            txs = data.get("data", {}).get("transactions", [])
            for tx in txs:
                for sub in tx.get("txHashList", []):
                    for r in sub.get("instructions", {}).get("receive", []):
                        tok = r.get("tokenInfo", {})
                        ca = tok.get("contractAddress")
                        if not ca:
                            continue
                        # Heuristic for NFT: decimals == 0 or explicit tokenId or symbol == ERC721
                        if tok.get("decimals") == 0 or tok.get("tokenId") is not None or tok.get("symbol") == "ERC721":
                            ca_cs = Web3.to_checksum_address(ca)
                            if ca_cs not in contracts:
                                contracts[ca_cs] = {"symbol": tok.get("symbol", ""), "tokens": set()}
                            if tok.get("tokenId"):
                                contracts[ca_cs]["tokens"].add(str(tok.get("tokenId")))
    except Exception as e:
        print(f"[!] Warning reading BAW tx history: {e}", file=sys.stderr)
    return contracts

def fetch_element_market_metrics(api_key, chain, ca):
    headers = {}
    if api_key:
        headers["X-api-key"] = api_key

    result = {
        "floor_price_base": None,
        "floor_price_usd": None,
        "top_offer_base": None,
        "top_offer_usd": None,
        "element_url": f"https://element.market/assets/{chain}/{ca}"
    }

    # Floor Price (side=1, listing)
    url_floor = f"https://api.element.market/openapi/v1/orders/list?chain={chain}&asset_contract_address={ca}&side=1&limit=1"
    try:
        rf = requests.get(url_floor, headers=headers, timeout=10)
        if rf.status_code == 200:
            orders = rf.json().get("data", {}).get("orders", [])
            if orders:
                result["floor_price_base"] = orders[0].get("priceBase")
                result["floor_price_usd"] = orders[0].get("priceUSD")
    except Exception:
        pass

    # Top Offer (side=0, collection/token bid)
    url_offer = f"https://api.element.market/openapi/v1/orders/list?chain={chain}&asset_contract_address={ca}&side=0&limit=1"
    try:
        ro = requests.get(url_offer, headers=headers, timeout=10)
        if ro.status_code == 200:
            orders = ro.json().get("data", {}).get("orders", [])
            if orders:
                result["top_offer_base"] = orders[0].get("priceBase")
                result["top_offer_usd"] = orders[0].get("priceUSD")
    except Exception:
        pass

    return result

def main():
    parser = argparse.ArgumentParser(description="Scan BAW NFT holdings and query Element Market floor/offers.")
    parser.add_argument("--wallet", type=str, help="Target wallet address (defaults to active BAW wallet)")
    parser.add_argument("--chain", type=str, default="bsc", help="EVM chain: bsc (default), ethereum, base, polygon")
    parser.add_argument("--rpc", type=str, help="Custom EVM RPC URL")
    parser.add_argument("--api-key", type=str, help="Element Market OpenAPI key (or set ELEMENT_API_KEY env)")
    parser.add_argument("--depth", type=int, default=100, help="Transaction history scan depth (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    chain = args.chain.lower()
    wallet = resolve_baw_wallet(args.wallet)
    api_key = load_element_api_key(args.api_key)

    rpc_url = args.rpc or DEFAULT_RPC_MAP.get(chain)
    if not rpc_url:
        print(f"[ERROR] Unsupported chain: {chain}. Provide --rpc URL.", file=sys.stderr)
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"[ERROR] Failed to connect to RPC: {rpc_url}", file=sys.stderr)
        sys.exit(1)

    if not args.json:
        print(f"[*] Scanning BAW NFT holdings for: {wallet}")
        print(f"[*] Network: {chain.upper()} | RPC: {rpc_url}")
        if not api_key:
            print("[!] Note: Running without Element API key (public rate limits apply).")

    candidates = scan_baw_nft_contracts(depth=args.depth)
    held_items = []

    for ca, meta in candidates.items():
        try:
            contract = w3.eth.contract(address=ca, abi=ERC721_ABI)
            bal = contract.functions.balanceOf(wallet).call()
            if bal > 0:
                try:
                    name = contract.functions.name().call()
                except Exception:
                    name = meta.get("symbol") or "Unknown NFT"
                try:
                    symbol = contract.functions.symbol().call()
                except Exception:
                    symbol = ""

                metrics = fetch_element_market_metrics(api_key, chain, ca)
                held_items.append({
                    "contract_address": ca,
                    "name": name,
                    "symbol": symbol,
                    "balance": bal,
                    "token_ids": sorted(list(meta.get("tokens", []))),
                    **metrics
                })
        except Exception:
            continue

    # Sort collections with active floor or top offer first
    held_items.sort(
        key=lambda x: (
            (x["floor_price_base"] is not None) or (x["top_offer_base"] is not None),
            x["floor_price_base"] or 0.0,
            x["balance"]
        ),
        reverse=True
    )

    if args.json:
        output = {
            "success": True,
            "wallet": wallet,
            "chain": chain,
            "total_collections": len(held_items),
            "total_tokens_held": sum(x["balance"] for x in held_items),
            "collections": held_items
        }
        print(json.dumps(output, indent=2))
        return

    # CLI Table Output
    if not held_items:
        print("[-] No active NFT holdings discovered.")
        return

    total_tokens = sum(x["balance"] for x in held_items)
    print(f"\n[+] Discovered {len(held_items)} NFT Collections | {total_tokens} Total Tokens Held\n")
    print(f"{'NFT Name':<28} | {'Qty':<4} | {'Floor Price':<22} | {'Top Offer':<22} | {'Contract Address'}")
    print("-" * 115)

    native_sym = "BNB" if chain == "bsc" else "ETH" if chain in ["ethereum", "base"] else "POL"

    for item in held_items:
        token_str = f" (#{', #'.join(item['token_ids'])})" if item['token_ids'] else ""
        disp_name = (item["name"] + token_str)[:27]

        floor_str = (
            f"{item['floor_price_base']} {native_sym} (${item['floor_price_usd']:.2f})"
            if item["floor_price_base"] is not None
            else "No Listing"
        )
        offer_str = (
            f"{item['top_offer_base']} {native_sym} (${item['top_offer_usd']:.2f})"
            if item["top_offer_base"] is not None
            else "No Offer"
        )

        print(f"{disp_name:<28} | {item['balance']:<4} | {floor_str:<22} | {offer_str:<22} | {item['contract_address']}")

if __name__ == "__main__":
    main()
