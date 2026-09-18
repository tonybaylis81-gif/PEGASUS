import os
from pegasus.autonomy import AutonomousCycle
from pegasus.core import Pegasus

def main():
    vault_path = os.environ.get("VALHALLA_VAULT_PATH", "VALHALLA ENGINEERING VAULT")
    result = AutonomousCycle(Pegasus(), vault_path).run()
    print(result)

if __name__ == "__main__":
    main()
