import argparse
from pegasus.portable import bootstrap_from_portable


def main():
    parser = argparse.ArgumentParser(description="Initialize PEGASUS on a new computer.")
    parser.add_argument("root", help="Path to the PEGASUS portable drive/root")
    args = parser.parse_args()
    print(bootstrap_from_portable(args.root))


if __name__ == "__main__":
    main()
