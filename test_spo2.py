"""Teste isolado de leitura de SPO2 em tempo real. Rodar com: python test_spo2.py"""

import asyncio
from colmi_r02_client.client import Client

RING_ADDRESS = "30:36:44:34:F5:06"


async def main():
    async with Client(RING_ADDRESS) as ring:
        print("Lendo SPO2, aguarde...")
        result = await ring.get_realtime_spo2()
        print(f"SPO2: {result}")


if __name__ == "__main__":
    asyncio.run(main())
