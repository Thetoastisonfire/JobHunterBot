"""
build.py

Manual build of the database.

"""

from synonym_finder_v2.ONET_db.build_onet_db import build_db


def main():
    #if not Path(ONET_DB_PATH).exists(): # if the database doesn't exist, make it
    build_db()


if __name__ == "__main__":
    main()
