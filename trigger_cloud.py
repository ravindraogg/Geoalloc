from huggingface_hub import HfApi, create_repo, upload_file
import os

def trigger_cloud_training():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN not found.")
        return

    api = HfApi(token=token)
    username = api.whoami()["name"]
    repo_id = f"{username}/geoalloc-training-data"
    
    print(f"1. Creating dataset repo: {repo_id}")
    try:
        create_repo(repo_id, repo_type="dataset", exist_ok=True)
    except Exception as e:
        print(f"Repo exists or error: {e}")

    print("2. Uploading train.jsonl...")
    upload_file(
        path_or_fileobj="geoalloc-env/train.jsonl",
        path_in_repo="train.jsonl",
        repo_id=repo_id,
        repo_type="dataset"
    )

    print("3. Dataset is ready at Hugging Face.")
    print("-----------------------------------")
    print("FINAL STEP: Go to https://huggingface.co/autotrain")
    print(f"Select your new dataset: {repo_id}")
    print("Select Model: unsloth/llama-3-8b-bnb-4bit")
    print("Click 'Start Training'!")

if __name__ == "__main__":
    trigger_cloud_training()
