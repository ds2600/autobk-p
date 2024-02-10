# autobk-p

AutoBk is a backup script to automatically backup obscure devices. 

AutoBk-P is the original, although it is currently being rewritten in Rust ([AutoBk-R](https://github.com/ds2600/autobk-r))

[AutoBk Controller](https://github.com/ds2600/autobk-controller) is a web interface designed to work with either AutoBk-P or AutoBk-R.

## Devices Supported
- Arris APEX-1000
- Arris CAP-1000
- Alpha CXC-HP
- Synamedia DCM 9902
- WISI Inca 4440
- Monroe OneNet
- Sonifex PSSend
- Arris Quartet
- Vecima TC600E
- Vecima CableVista

## Dependencies
```bash 
sudo apt update
sudo apt install python3 python3-pip
```
## Usage

1. Clone the repository
```bash
git clone https://github.com/ds2600/autobk-p.git
cd autobk-p
```

2. Create a virtual environment
```bash 
python3 -m venv venv
source venv/bin/activate
```

3. Install the required dependencies
```bash
pip3 install -r requirements.txt
```

4. Modify autobk.ini with your database credentials

5. Run the script
```bash
python3 srvc_autobk.py
```
