"""
Scan sem filtro de nome - mostra TODOS os dispositivos BLE encontrados.
Útil pra anéis mais novos (R08/R09/R10+) que não estão na lista de
prefixos hardcoded do colmi_r02_util scan.

Rodar com: python scan_raw.py
"""

import asyncio
from bleak import BleakScanner


async def main():
    print("Escaneando por 10 segundos... deixe o anel por perto.\n")
    devices = await BleakScanner.discover(timeout=10.0)

    if not devices:
        print("Nenhum dispositivo BLE encontrado. Verifique se o Bluetooth do Windows está ligado.")
        return

    print(f"{'Nome':<30} | Endereço")
    print("-" * 60)
    for d in devices:
        name = d.name or "(sem nome)"
        print(f"{name:<30} | {d.address}")

    print("\nProcure na lista acima algo que pareça com o nome do seu anel")
    print("(costuma ter 'R10' ou 'COLMI' ou parecido no nome).")


if __name__ == "__main__":
    asyncio.run(main())
