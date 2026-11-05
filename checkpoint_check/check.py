import torch

ckpt = torch.load(
    r"D:\dev\Hunyuan3D\fine-tune-08\ckpt-step=00008000.ckpt\out\pytorch_model.bin",
    map_location="cpu",
    weights_only=True
)

if "state_dict" in ckpt:
    ckpt = ckpt["state_dict"]

print("Total parameters:", len(ckpt))

lora_keys = [
    k for k in ckpt
    if "lora_" in k.lower()
]

print("LoRA parameters:", len(lora_keys))
print("Examples:", lora_keys[:15])
