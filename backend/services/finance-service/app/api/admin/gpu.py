"""GPU instance management - AWS EC2 start/stop."""
import logging
import boto3
import httpx
from fastapi import APIRouter, Depends
from common.dependencies import get_current_user, require_role
from common.models.user import User

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
    private_ip = inst.get("PrivateIpAddress")
    instance_type = inst.get("InstanceType", "g6.xlarge")

    # Check Ollama if running (use private IP -- security group blocks public access to 11434)
    ollama_status = "offline"
    models = []

    if state == "running" and private_ip:
        try:
            r = httpx.get(f"http://{private_ip}:11434/api/tags", timeout=5.0)
            if r.status_code == 200:
                ollama_status = "ready"
                models = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            ollama_status = "starting"

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
async def gpu_start(current_user: User = Depends(require_role("admin"))):
    """Start GPU instance. Admin only."""
    ec2 = get_ec2()
    ec2.start_instances(InstanceIds=[INSTANCE_ID])
    logger.info("GPU instance %s starting (by %s)", INSTANCE_ID, current_user.email)
    return {"status": "starting", "message": "GPU instance is starting... (1-2 min)"}

@router.post("/gpu/stop")
async def gpu_stop(current_user: User = Depends(require_role("admin"))):
    """Stop GPU instance. Admin only."""
    ec2 = get_ec2()
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    logger.info("GPU instance %s stopping (by %s)", INSTANCE_ID, current_user.email)
    return {"status": "stopping", "message": "GPU instance is shutting down..."}
