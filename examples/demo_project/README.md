# Django Solana Payments - Demo Project

This is a demonstration project showing how to integrate and use the `django-solana-payments` library.

## Installation

Install the library from the parent directory:

```bash
pip3 install ../../.
```

## Setup

1. Run migrations:
```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

2. Start the development server:
```bash
python3 manage.py runserver
```

Or use the convenience script:
```bash
./dev_server.sh
```

## Features Demonstrated

### 1. Custom Models
See `payments/models.py` for examples of extending the base payment models with custom fields.

### 2. Signal Handlers
The `payments/signals.py` file demonstrates how to use the `solana_payment_accepted` signal to customize payment processing:

- **Email notifications** - Send confirmation emails when payments are accepted
- **Order processing** - Update order status based on payment verification
- **Access control** - Grant premium features or subscriptions
- **Analytics tracking** - Log payments to analytics services

### 3. Admin Customization
Custom admin interface for managing payments and tokens.

## Testing on Devnet

### Setup Solana CLI

1. Generate a new keypair:
```bash
solana-keygen new --outfile devnet.json
```

2. Configure for devnet:
```bash
solana config set --url https://api.devnet.solana.com
solana config set --keypair devnet.json
```

3. Check your address:
```bash
solana address
```

4. Get devnet SOL:
```bash
solana airdrop 2
```

5. Transfer SOL to a payment address:
```bash
solana transfer <ADDRESS> 0.2 --allow-unfunded-recipient
```

### SPL Tokens (USDC)

- **Devnet USDC Faucet**: https://spl-token-faucet.com/?token-name=USDC-Dev
- **Devnet USDC Mint Address**: `Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr`

## Development

To quickly test code changes from the library:

```bash
./dev_server.sh
```

This script will:
1. Uninstall the current version
2. Install the latest version from the parent directory
3. Start the development server
