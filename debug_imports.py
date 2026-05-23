import rule_engine
import engines
import dashboard

print("rule_engine:", rule_engine.__file__)
print("has betting:", hasattr(rule_engine, "get_betting_signals"))
