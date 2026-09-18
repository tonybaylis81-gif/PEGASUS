import argparse
from pegasus.portable import backup_portable


def main():
    parser = argparse.ArgumentParser(description="Back up the complete PEGASUS portable root.")
    parser.add_argument("root", help="PEGASUS root directory")
    parser.add_argument("destination", help="Output archive path without extension")
    args = parser.parse_args()
    print(backup_portable(args.root, args.destination))


if __name__ == "__main__":
    main()
