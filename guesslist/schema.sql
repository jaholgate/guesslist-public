DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS club;
DROP TABLE IF EXISTS round;
DROP TABLE IF EXISTS song;
DROP TABLE IF EXISTS guess;

CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  email TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  club_id INTEGER,
  score INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (club_id) REFERENCES club (id)
);

CREATE TABLE IF NOT EXISTS club (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  name TEXT NOT NULL,
  admin_id INTEGER NOT NULL,
  FOREIGN KEY (admin_id) REFERENCES user (id)
);

CREATE TABLE IF NOT EXISTS round (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  name TEXT NOT NULL,
  description NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  playlist_url TEXT,
  club_id INTEGER NOT NULL,
  FOREIGN KEY (club_id) REFERENCES club (id)
);

CREATE TABLE IF NOT EXISTS song (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  artist TEXT NOT NULL,
  name TEXT NOT NULL,
  image_url TEXT,
  spotify_track_id TEXT NOT NULL,
  user_id NOT NULL,
  round_id INTEGER NOT NULL,
  club_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (round_id) REFERENCES round (id),
  FOREIGN KEY (club_id) REFERENCES club (id)
);

CREATE TABLE IF NOT EXISTS guess (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  guess_user_id NOT NULL,
  guess_username NOT NULL,
  comment TEXT,
  user_id INTEGER NOT NULL,
  song_id INTEGER NOT NULL,
  round_id INTEGER NOT NULL,
  club_id INTEGER NOT NULL,
  points INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (guess_user_id) REFERENCES user (id),
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (song_id) REFERENCES song (id),
  FOREIGN KEY (round_id) REFERENCES round (id),
  FOREIGN KEY (club_id) REFERENCES club (id)
);