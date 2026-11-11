"""Activate the explicitly requested local research detector after benchmarking."""
import hashlib
import json
import shutil
from pathlib import Path


def main():
    root=Path('models/image')
    model=root/'detectra-openfake/model.onnx'
    expected='b5bd0fd699469b721b00f6a5626a2616b2b0a34283eece124d90451147ab7fc6'
    assert hashlib.sha256(model.read_bytes()).hexdigest()==expected
    experiment=Path('research/experiments/openfake-pretrained')
    metrics=json.loads((experiment/'metrics.json').read_text())
    assert metrics['count']==120
    backup=root/'registry-before-openfake.json'
    if not backup.exists():shutil.copy2(root/'registry.json',backup)
    record=dict(name='image',version='image-detector-v5-openfake-experimental',architecture='OpenFake fine-tuned ViT-S/16, quantized ONNX',runtime='openfake_onnx',file_path='detectra-openfake/model.onnx',sha256=expected,threshold=.95,calibration='publisher_platt_scaling',deployment_status='experimental_local',classes={'0':'real','1':'ai_generated'},source={'repository':'s-gehring/detectra-openfake','revision':'c84565e5bf8969d95908e12844f551e77ae87105','license':'CC-BY-NC-4.0; additional upstream terms documented in model card'},training_dataset='Publisher OpenFake fine-tuning with modern generators, photos, paintings and charts; no local fine-tuning of this checkpoint',regression_metrics=metrics['candidate'],experiment=str(experiment),limitation='Noncommercial research detector. Publisher scaling and 95% cutoff, not locally calibrated. Local diagnostic sample: 112/120 binary decisions correct; 0/60 real images flagged, 8/60 AI images missed. Previously examined datasets; possible upstream overlap. Abstention can reduce coverage. Not representative field accuracy or proof of origin. Images remain local.')
    temp=root/'registry.pending.json';temp.write_text(json.dumps(record,indent=2));temp.replace(root/'registry.json')
    (experiment/'activation.json').write_text(json.dumps(dict(version=record['version'],backup=str(backup),activation='User-requested local experimental replacement; not validated production release'),indent=2))
    print(record['version'])


if __name__=='__main__':main()
