"""Case view derived from persisted evidence; shared entities never imply guilt."""
from sqlalchemy import select
from app.models.cases import Case, CaseAsset
from app.models.database import Analysis
from app.models.intelligence import AnalysisEntity, Entity
from app.services.auth import principal, allowed_analysis_ids
from app.core.config import settings


def assess_case(db, case_id, analyses):
    ids = [a.id for a in analyses]
    scenarios, conflicts, gaps, synthetic = [], [], [], []
    for analysis in analyses:
        report = analysis.report or {}
        node_labels = {n['id']: n.get('label', n['id']) for n in report.get('graph', {}).get('nodes', [])}
        for scenario in report.get('scenarios', []):
            scenarios.append(dict(scenario, analysis_id=analysis.id, asset_path_labels=[node_labels.get(n,n) for n in scenario.get('asset_path',[])]))
        for conflict in report.get('conflicts', []):
            conflicts.append(dict(conflict, analysis_id=analysis.id))
        if analysis.state not in ('COMPLETED', 'PARTIAL'):
            gaps.append(dict(analysis_id=analysis.id, reason='Investigation '+analysis.state.lower()))
        for evidence in report.get('evidence', []):
            if evidence.get('label') in ('unavailable','verification_unavailable'):
                gap=dict(analysis_id=analysis.id, reason=evidence.get('explanation', 'Check unavailable'))
                if gap not in gaps:gaps.append(gap)
            if evidence.get('category') in ('synthetic_media','manipulation'):
                synthetic.append(dict(analysis_id=analysis.id, evidence_id=evidence['id'], label=evidence.get('label'), score=evidence.get('score'), verdict=evidence.get('metadata',{}).get('verdict','unavailable')))
    entity_ids = select(AnalysisEntity.entity_id).where(AnalysisEntity.analysis_id.in_(ids))
    query = (select(Entity, Case).join(AnalysisEntity, AnalysisEntity.entity_id==Entity.id)
             .join(CaseAsset, CaseAsset.analysis_id==AnalysisEntity.analysis_id)
             .join(Case, Case.id==CaseAsset.case_id)
             .where(Entity.id.in_(entity_ids), Case.id!=case_id,
                    Entity.type.in_(['UPI_ID','EMAIL','DOMAIN','PHONE_NUMBER','URL','FILE_HASH']))
             .distinct().order_by(Case.created_at, Entity.id).limit(100))
    if settings.auth_required:
        query=query.where(Case.owner_id==principal.get()['id'], AnalysisEntity.analysis_id.in_(allowed_analysis_ids()))
    correlations=[dict(entity_id=e.id, entity_type=e.type, value=e.display_value, case_id=c.id, case_title=c.title, significance='Shared identifier; operator identity and malicious intent are not established') for e,c in db.execute(query).all()] if ids else []
    actions=list(dict.fromkeys(action for s in scenarios for action in s.get('recommendations',[])))
    if correlations:actions.append('Review the linked cases and compare the shared identifier; repetition alone is not evidence of fraud.')
    if conflicts:actions.append('Resolve conflicting evidence before drawing a conclusion.')
    if not actions:actions.append('Review completed checks and independently verify consequential claims.')
    return dict(title='Potential fraud chain requires review' if scenarios else 'No supported fraud scenario identified', scenarios=scenarios, correlations=correlations, conflicts=conflicts, synthetic_findings=synthetic, gaps=gaps[:100], recommendations=actions, scope='Derived from saved case investigations. AI origin and shared entities alone do not increase cybersecurity risk.', completed=sum(a.state=='COMPLETED' for a in analyses), partial=sum(a.state=='PARTIAL' for a in analyses), total=len(analyses))
