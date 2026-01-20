<img width="1920" height="1032" alt="bild" src="https://github.com/user-attachments/assets/92c6215d-a7e7-4978-ab29-873c0e5e5ad9" />


## TO DO
Upload files
Fix the "black line" on the cover (should be transparent)
fix the progress bar for playing song (it "works" but when changing possition it starts to play correctly but the progress bar go to 0)

## Install HeartMuLa

```bash
conda create -n heartlib python=3.10
conda activate heartlib
git clone https://github.com/HeartMuLa/heartlib
cd heartlib
pip install -e .

pip install huggingface_hub[hf_xet]

hf download --local-dir "./ckpt" "HeartMuLa/HeartMuLaGen"
hf download --local-dir "./ckpt/HeartMuLa-oss-3B" "HeartMuLa/HeartMuLa-oss-3B"
hf download --local-dir "./ckpt/HeartCodec-oss" "HeartMuLa/HeartCodec-oss"

pip install pyarrow==20.0.0
pip install triton-windows==3.5.1.post24
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu124
```

## Manual install requirements for GUI

```bash
pip install customtkinter>=5.2.0
pip install Pillow>=10.0.0
pip install pygame>=2.5.0
pip install darkdetect>=0.8.0
pip install tkinterdnd2>=0.4.0
```

desas då

## Install GUI

Copy:
```bash
start_studio.bat
requirements.txt
gui.py
```
to the root folder of heartlib.
cmd from folder
```bash
pip install -r requirements.txt
```
Open start_studio.bat
thats it, you will see the progress in CMD.

I will add more features to modify and make faster generations. I sort of thinking on adding seed so its possible to create a 10-15 seconds clip and if you like it continue creating the full.

License:
I will update this!
