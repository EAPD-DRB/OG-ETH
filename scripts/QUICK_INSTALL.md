# Quick install

Pre-req: **git** installed. Nothing else.

## macOS / Linux

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/EAPD-DRB/OG-ETH/main/scripts/install.sh)" _ --repo og-eth
```

## Windows (PowerShell)

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/EAPD-DRB/OG-ETH/main/scripts/install.ps1))) -Repo og-eth
```

## Skip the prompts

```bash
# macOS / Linux -- clones to ~/Projects/OG-ETH
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/EAPD-DRB/OG-ETH/main/scripts/install.sh)" _ --repo og-eth --dest ~/Projects --yes
```

```powershell
# Windows -- clones to C:\Users\<you>\Projects\OG-ETH
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/EAPD-DRB/OG-ETH/main/scripts/install.ps1))) -Repo og-eth -Dest C:\Users\$env:USERNAME\Projects -Yes
```

## After install

Activate the venv and you're set:

```bash
# macOS / Linux
cd <destination>
source .venv/bin/activate
python -W ignore -c "import ogeth; print(ogeth.__version__)"
```

```powershell
# Windows
cd <destination>
.\.venv\Scripts\Activate.ps1
python -W ignore -c "import ogeth; print(ogeth.__version__)"
```

## Manual download (inspect before running)

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/EAPD-DRB/OG-ETH/main/scripts/install.sh -o install.sh
less install.sh   # inspect
bash install.sh --repo og-eth
```

```powershell
# Windows
Invoke-WebRequest -UseBasicParsing -Uri https://raw.githubusercontent.com/EAPD-DRB/OG-ETH/main/scripts/install.ps1 -OutFile install.ps1
notepad install.ps1   # inspect
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Repo og-eth
```

The installer is universal — it works for any uv-migrated OG country repo. Run it without `--repo` / `-Repo` to pick from a menu instead of going straight to OG-ETH.
