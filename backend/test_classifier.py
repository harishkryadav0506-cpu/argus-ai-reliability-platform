from app.ml.failure_prediction import FailureClassifier, FailureCategory
from app.services.simulation_service import SimulationEngine, FaultType

engine = SimulationEngine()
classifier = FailureClassifier()

print("--- Testing Classifier on Fault Distortions ---")
for fault in FaultType.ALL:
    engine.inject_fault(fault, severity="high", duration_seconds=60)
    for i in range(3):
        point = engine.tick()
        res = classifier.classify(point["metrics"])
        print(f"{fault:20} -> Classified: {res['category']:20} Conf: {res['confidence']}")
    engine.reset_to_normal()
