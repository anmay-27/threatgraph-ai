"""Install only after the predefined paired evaluation gate succeeds."""
import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

def main():
    output = Path('research/experiments/image-community-v3')
    audit = json.loads((output/'metrics.json').read_text())
    new,old = audit['candidate']['test'],audit['baseline']['test']
    passed = (new['balanced_accuracy'] >= old['balanced_accuracy']+.02 and new['recall'] >= old['recall'] and new['false_positive_rate'] <= old['false_positive_rate'] and audit['candidate']['ood']['balanced_accuracy'] >= audit['baseline']['ood']['balanced_accuracy'])
    if not passed:
        print('Candidate failed the predefined gate; installed model preserved.')
        return
    directory = Path('models/image/community-forensics-384')
    checkpoint = directory/'model.safetensors'
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != audit['model_sha256']:
        raise ValueError('Evaluated checkpoint hash mismatch')
    if hashlib.sha256(Path('models/image/project-trained-v2.pt').read_bytes()).hexdigest() != audit['baseline_sha256']:
        raise ValueError('Baseline changed after evaluation')
    calibration = audit['calibration'] | dict(checkpoint_sha256=audit['model_sha256'])
    (directory/'calibration.json').write_text(json.dumps(calibration,indent=2))
    registry = Path('models/image/registry.json')
    backup = registry.with_name('registry-before-v3.json')
    if not backup.exists():
        shutil.copyfile(registry,backup)
    record = dict(name='image',version='image-detector-v3-community-forensics',architecture='ViT-small/16 (384px)',file_path='community-forensics-384/model.safetensors',runtime='community_forensics',threshold=calibration['threshold'],temperature=calibration['temperature'],calibration='temperature_scaling',calibration_date=datetime.now(timezone.utc).isoformat(),deployment_status='research_calibrated',training_dataset='OwensLab/CommunityForensics (upstream pretrained weights)',local_calibration_dataset='datasets/prepared/tiny-genimage-v3',test_metrics=new,validation_metrics=audit['candidate']['validation'],cross_generator_metrics=audit['candidate']['ood'],source=json.loads((directory/'source.json').read_text()),experiment=str(output),sha256=audit['model_sha256'],classes={'0':'real','1':'ai_generated'},limitation='Official third-party pretrained image detector with local calibration. Scores measured on a small fixed GenImage subset; upstream training/pretraining overlap cannot be excluded. Not verified on all modern generators, documents or screenshots. No validated OOD gate or pixel localization. AI origin alone is not malicious intent.')
    temporary = registry.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(record,indent=2))
    temporary.replace(registry)
    print(json.dumps({'installed':record['version'],'test':new,'baseline':old,'threshold':record['threshold']},indent=2))

if __name__ == '__main__':
    main()
