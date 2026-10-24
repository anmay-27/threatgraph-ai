from app.fusion.features import vector


def predict(model, evidence, conflicts):
    return float(model.predict_proba([vector(evidence, conflicts)])[0, 1])
