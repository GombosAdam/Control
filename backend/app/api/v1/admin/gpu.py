"""GPU instance management - AWS EC2 start/stop."""
import logging
import boto3
import httpx
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

INSTANCE_ID = "i-06842b125fc6598cd"
REGION = "eu-central-1"

def get_ec2():
    return boto3.client("ec2", region_name=REGION)

@router.get("/gpu/status")
async def gpu_status(current_user: User = Depends(get_current_user)):
    """Get GPU instance status, IP, and Ollama health."""
    ec2 = get_ec2()
    resp = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    inst = resp["Reservations"][0]["Instances"][0]

    state = inst["State"]["Name"]
    public_ip = inst.get("PublicIpAddress")
    instance_type = inst.get("InstanceType", "g4dn.xlarge")

    # Check Ollama if running
    ollama_status = "offline"
    models = []
    gpu_info = None

    if state == "running" and public_ip:
        try:
            r = httpx.get(f"http://{public_ip}:11434/api/tags", timeout=5.0)
            if r.status_code == 200:
                ollama_status = "ready"
                models = [m["name"] for m in r.json().get("models", [])]
        except:
            ollama_status = "starting"

        # GPU info is static for T4, no need to probe

    return {
        "instance_id": INSTANCE_ID,
        "instance_type": instance_type,
        "state": state,
        "public_ip": public_ip,
        "ollama_status": ollama_status,
        "models": models,
        "ollama_url": f"http://{public_ip}:11434" if public_ip else None,
        "gpu": {
            "name": "NVIDIA L4",
            "vram": "24 GB GDDR6",
            "cuda_cores": 7424,
            "compute": "8.9",
        },
        "cost_per_hour": 0.98,
    }

@router.post("/gpu/start")
async def gpu_start(current_user: User = Depends(get_current_user)):
    """Start GPU instance."""
    ec2 = get_ec2()
    ec2.start_instances(InstanceIds=[INSTANCE_ID])
    logger.info(f"GPU instance {INSTANCE_ID} starting (by {current_user.email})")
    return {"status": "starting", "message": "GPU instance is starting... (1-2 min)"}

@router.post("/gpu/stop")
async def gpu_stop(current_user: User = Depends(get_current_user)):
    """Stop GPU instance."""
    ec2 = get_ec2()
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    logger.info(f"GPU instance {INSTANCE_ID} stopping (by {current_user.email})")
    return {"status": "stopping", "message": "GPU instance is shutting down..."}
