import os
import yaml
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.cli import CLI
from ansible.parsing.dataloader import DataLoader


def decrypt_vault(
        filename, vault_password=None, vault_password_file=None, vault_prompt=False
):
    """
    filename: name of your encrypted file that needs decrypted.
    vault_password: key that will decrypt the vault.
    vault_password_file: file containing key that will decrypt the vault.
    vault_prompt: Force vault to prompt for a password if everything else fails.
    """

    loader = DataLoader()
    if vault_password:
        vault_secret = [([], VaultSecret(vault_password.encode()))]
    elif vault_password_file:
        vault_secret = CLI.setup_vault_secrets(
            loader=loader, vault_ids=[vault_password_file]
        )
    else:
        vault_secret = CLI.setup_vault_secrets(
            loader=loader, vault_ids=[], auto_prompt=vault_prompt
        )

    vault = VaultLib(vault_secret)

    with open(filename) as f:
        unencrypted_yaml = vault.decrypt(f.read())
        unencrypted_yaml = yaml.safe_load(unencrypted_yaml)
        return unencrypted_yaml

def get_credentials():
    credentials = decrypt_vault(
    filename="/home/kamil/Network_Interface/nornir_data/encrypted_credentials.yaml",
    vault_password=os.environ.get("SECRET_PASSWORD"),
    )
    return credentials