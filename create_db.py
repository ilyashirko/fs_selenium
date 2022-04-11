import sqlite3

from environs import Env


def create_tables(fs, cursor):
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS matches(
            match_id TEXT,
            country TEXT,
            championship TEXT,
            timestamp INTEGER,
            home_team TEXT,
            guest_team TEXT,
            home_result INTEGER,
            guest_result INTEGER,
            extended_home_result INTEGER,
            extended_guest_result INTEGER,
            url TEXT
        );
        """
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS games(
            match_id TEXT,
            key TEXT,
            queue INTEGER,
            timestamp INTEGER,
            home_team TEXT,
            guest_team TEXT,
            home_result INTEGER,
            guest_result INTEGER,
            extended_home_result INTEGER,
            extended_guest_result INTEGER
        );
        """
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS statistics(
            match_id TEXT,
            place INTEGER,
            team TEXT,
            games INTEGER,
            win INTEGER,
            draw INTEGER,
            lose INTEGER,
            goals_scored INTEGER,
            goals_conceded INTEGER,
            points INTEGER
        );
        """
    )
    fs.commit()


if __name__ == '__main__':
    env = Env()
    env.read_env()

    fs = sqlite3.connect(env.str('DATABASE'))
    cursor = fs.cursor()

    create_tables(fs, cursor)
