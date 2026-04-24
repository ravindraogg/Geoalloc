import json
import os

def convert_for_autotrain():
    input_path = "geoalloc-env/training_observations.json"
    output_path = "geoalloc-env/train.jsonl"
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    with open(input_path, "r") as f:
        data = json.load(f)

    # AutoTrain likes a 'text' column containing the full prompt + completion
    # Since we are doing supervised/fine-tuning style via AutoTrain:
    with open(output_path, "w") as f:
        for entry in data:
            # We wrap the state into the prompt
            prompt = f"Objective: Sustain global stability. Observation: {json.dumps(entry)} Action:"
            # For AutoTrain, we usually provide a 'text' field
            json.dump({"text": prompt}, f)
            f.write("\n")
            
    print(f"Success! Created {output_path} for AutoTrain CLI.")

if __name__ == "__main__":
    convert_for_autotrain()
