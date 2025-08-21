
# MindVault-AI Payments Bootstrap
Klaar-om-te-gaan templates (Node.js **of** Python) om **webhooks** te verwerken en **wallet credits + bonusloten** toe te kennen met data uit `mindvaultai_bundles_psp.json`.

## Snel starten (Node.js)
```bash
cd node
cp .env.sample .env   # vul DB pad en secrets als nodig
npm i
npm run dev
# Test
curl -X POST http://localhost:8787/webhook/crypto -H "Content-Type: application/json" -d '{"eventId":"evt_test_1","userId":"user_123","amount":10,"currency":"EUR","txId":"onchain_abc"}'
```

## Snel starten (Python)
```bash
cd python
cp .env.sample .env
pip install -r requirements.txt
uvicorn main:app --port 8788 --reload
# Test
curl -X POST http://localhost:8788/webhook/crypto -H "Content-Type: application/json" -d '{"eventId":"evt_test_1","userId":"user_123","amount":10,"currency":"EUR","txId":"onchain_abc"}'
```

> **Belangrijk:** Productie-integratie met Mollie/PayPal vereist **signature/verificatie**. In deze templates staat een `TODO` met de plek waar je dat toevoegt.
