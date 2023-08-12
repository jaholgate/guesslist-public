# guesslist
A music guessing game built using Flask, Spotify API and Tailwind CSS.

<https://guesslist.jamesholgate.co.uk>

1. Create a club and invite your friends.
2. In each round, submit songs on a theme.
3. guesslist creates a Spotify playlist of your songs.
4. Guess who submitted each song. Win points for correct guesses.
5. Track your points on the club leaderboard.

## Video demo

<https://youtu.be/sNwhhFeLuI0>

## How it works

- A user registers with their email address, username and password.
- The user creates a 'club' and gives it a name. This user is the 'club admin' for this club.
- A club defines a group of users who will play the game together.
- Each club is given a six-character club ID (via Hashids)
- The club admin (and any other users who join the club) can share the club ID to invite their friends to join their club.
- An 'invite link' is also generated, pointing to the registration page with the club id appended as a URL parameter. The registration form includes JavaScript to parse this URL parameter and fill the optional 'Club ID' field with this value.
- Alternatively, a user can register without a club ID and use the 'Join club' form later, entering the club ID here instead.
- A club can contain any number of rounds. Rounds are the themes on which users will submit songs e.g. 'cover songs', 'songs released 1999-2001'. When a club is created, five starter rounds are added by default.
- Each round has a name and description to explain the theme. It also has round status. At the start of the game, all rounds have the status 'pending' ('Upcoming' on the front-end).
- The club admin can access a 'manage club' page where they can rename the club, and add additional rounds.
- If the club admin views a pending/upcoming round, they can access a 'manage round' page where they can edit the name and description, or delete the round.
- Once at least three users have joined the club, the club admin is shown a 'Start game' button on the home screen. Starting the game will open the first round, and future rounds will open when the previous one closes. It also stops any more members from joining the club; at this time I have decided not to cater for users joining/leaving clubs while the game is in progress. Similarly, each user can currently only be a member of one club and cannot leave that club.
- Once the game has started, the status of the first round changes to 'open for songs'. On viewing the round, users are shown a form where they can enter a Spotify share URL and an optional comment on the song they are submitting.
- On submitting the form, the app parses the Spotify URL to find the track ID, and calls the Spotify API to retrive the track information. If the provided URL / track ID is valid (and has not already been submitted to this round) then the track details (artist, title, cover artwork URL etc) are stored in the song table in the database. On viewing the round page, the user is now shown what song they submitted.
- When the last user in the club submits a song to a round, the app calls the Spotify API and passes in all the submitted tracks to create a playlist. The round status changes to 'open for guesses'.
- On viewing the round page, users will now see a link to the Spotify playlist and a form where they can guess which user submitted each song in the round. They can select a username from a select / drop-down, and optionally add a comment on each song. The form uses JavaScript to ensure that the user has added a guess for each song, and that their guesses are unique i.e. they're not guessing the same user for more than one song.
- On submitting their guesses, guesses are stored in the guess table in database. Points are calculated (1 point for a correct guess) but are not yet shown to users.
- Once the last user in the club has submitted their guesses, the round page will now show for each song: who submitted it, the guesses and comments submitted, the points awarded for correct guesses.
- The next round opens automatically, and the cycle repeats until there are no rounds remaining.
- Users can view their total score across rounds on the leaderboard page.

## Database and data structures

Guesslist uses an sqlite database containing the following tables:

- user: to store login details, what club the user is a member of, score etc.
- club: to store club name, user id of the club admin.
- round: to store the name, description and status of each round.
- song: to store the songs submitted by users in each round.
- guess: to store the guesses submitted by users in each round.

Full details can be found in schema.sql

## Flask

The app uses Flask <https://flask.palletsprojects.com/>. Blueprints are used to define sections / screens in the app, their routes and application / game logic e.g. auth.py, club.py, round.py. Various helper functions e.g. database queries, email sends can be found in utilities.py.

## App structure

- root
  - app.py calls the create_app function in \_\_init\_\_.py
  - in development mode only, an /instance folder is required and contains app config (config.py) and guesslist.sqlite database
  - tailwind.config.js defines Tailwind CSS settings, most importantly the input and output CSS files
- guesslist
  - \_\_init\_\_.py creates the app, imports and initialises Flask Hashids and Mail. Registers blueprints with the app.
  - schema.sql defines the database tables
  - db.py initialises the sqlite database and defines the get_db function used throughout the app to perform database actions.
  - index.py defines the homepage route. The homepage route serves different content for logged-out / logged-in users, and for logged-in users depending on whether they are in a club and the status of that club.
  - club.py defines routes and logic for creating, joining and managing a club, and for displaying the club leaderboard.
  - round.py defines routes and logic for adding, managing, starting and deleting rounds. Also for submitting songs and guesses to a round.
  - utilities.py includes functions called from other files/routes, related to:
    - JSON Web Tokens used for 'reset password' feature
    - sending email via Flask Mail (using threading to send these asynchronously)
    - getting a new access token for the Spotify API
    - various get_db functions to get users, clubs, rounds, songs, guesses etc
    - join_club function used by both the 'register' and 'join club' routes
  - static
    - src contains input.css which defines Tailwind CSS base styles and components abstracted for re-use e.g. button styling
    - dist contains output.css which contains the compiled CSS generated by Tailwind CSS
    - guess.js adds client-side validation to the 'guess' form and concatenates the user's guesses for each song into a single value, to be parsed in round.py
    - register.js parses the club ID passed to the register page via a URL parameter, and sets the value of the 'Club ID' field accordingly.
  - templates - contains HTML / Jinja templates for the various pages / routes in the app. Jinja for-loops and if/else statements are used to display for example a list of rounds, or list of songs submitted to a round.

## Tailwind CSS

The app uses the Tailwind CSS framework <https://tailwindcss.com/>. Tailwind's utility classes are added to the HTML/Jinja templates. Button styling is used across the app and so is abstracted into a '.btn-primary' component.

## Spotify API

The app uses the Spotify API <https://developer.spotify.com/documentation/web-api> to create a playlist containing the songs added to each round. Individual users are not required to authenticate with their Spotify user accounts. Instead, the app is authenticated with a dedicted 'guesslist' Spotify user. API credentials were generated for this user and are used when making API calls to retrieve track information and create playlists. The playlists are public playlists owned by the 'guesslist' Spotify user. API credentials are stored in config.py locally. For production, the app is deployed on Fly.io and the credentials are stored in their 'secrets' feature.

## Hashids

Hashids (via the Flask Hashids module <https://pypi.org/project/Flask-Hashids/>) are used to hash numeric club and round IDs and display more 'random' looking six-character IDs to users in URLs. As described above, users must enter the hashed club ID when joining a club, either via the club invite link and 'register' page, or entering it manually on the 'join club' page.

## Email notifications

The app uses the Flask Mail module <https://pypi.org/project/Flask-Mail/> to send email notifications to users via Gmail. Gmail credentials are handled as per Spotify API credentials above. Email is used for password reset (see below) and -

Email notifications are sent to club members when:

- The game starts and first round opens for songs
- A playlist is generated and a round becomes open for guesses
- All guesses have been received in a round and are available to view (along with scores). And the next round is open for songs.

## User registration

Users can register with an email address, username and password. They can optionally enter a club ID if they have been invited to join one. A 'reset password' feature is implemented using JSON Web Tokens (JWT <https://jwt.io/>) and a 'password reset' link is sent to the user via email.

## Deployment

The app is deployed to <https://fly.io/> and can be found (and played) at <https://guesslist.jamesholgate.co.uk/>
