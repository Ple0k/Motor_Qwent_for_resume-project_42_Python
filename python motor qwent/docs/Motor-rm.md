Motor functioning

Summary :
I)    Rules of The Gwent
II)   Review of logic between Front, Back, Motor
III)  Review of the Database the motor uses
IV)   Review of how a motor game state is made
V)    Review of how the motor determines the possible plays
VI)   Review of how a player game state is made
VII)  Review of how the motor plays a turns out until next game state
VIII) Review of how AI pickup its plays
IX)   Review of choices made, and logs for the creation of the game

I)    Rules of The Gwent
Gwent is a versus card game between 2 Players.

Deck
A deck consists of 25 cards and 1 Player's power

Game Setup
A coin flip determines who goes first.
Each player draws 10 cards.
The player going first may Mulligan up to 3 cards, while the second player may Mulligan up to 2 cards.

To Mulligan X card(s):
Set X card(s) aside.
Draw X replacement card(s).
Shuffle the card(s) that were set aside back into the Deck.

Turn Structure
The Player may use their Commander, if possible.
The Player may use the unique Stratagem they have if they were the starting player.
The Stratagem isn't really considered a Card
The Player may play one card.
If the Player has no remaining possible actions, their turn automatically ends.
The Player may only press End Turn if they have already played a card.
If the player plays no cards even though they had a card they could have played, the game forces them to discard one card.

Playing a Card
A Card is played from hand.
If it's an unit it's placed on board
An units has a strength. Strength can be affected, if it reaches 0, the cards is destroyed.
Some cards can have special effects, they can requier targetting
A Spell is directly discarded once the effect has been resolved.
Dicarded or Destroyed cards join the Graveyard.

Passing the Round
Passing means that the player will no longer receive any turns until the end of the current round.
If a player ends their turn with 0 cards in hand, the game automatically makes them pass the round.
If a player uses their Commander or Stratagem, they can no longer pass the round during that turn.
If a player plays nothing during their turn, they may choose to pass the round.

End of a Round
When both players have passed, the round ends and the players' points are counted.
Points are determined by the sum of strength of the cards in the player's board
The winner receives one Crown.
In case of a tie, both players receive one Crown.

Start of a New Round
Both players draw as many cards as possible, up to a maximum of 3 cards.
The player who won the previous round goes first in the new round.
In case of a tie, the player who did not go first in the previous round goes first.

End of the Game
A player wins the game by winning:
2 rounds to 1, or
2 rounds to 0.

If the score reaches 2–2, the game ends in a draw.

The game also ends if:
A player presses Surrender.
The systems decides so


II)   Review of logic between Front, Back, Motor
Player vs Player (Notes difference vs AI)

2 Players gets matched, 
Back attributes randomly Player 1 playing first and Player 2 playing second.

The motor return either 0 or 1 or 2 or 3, and create/updates files.
If it returns 0 : No problem detected, game is ongoing, update both player, awating input from both player
If it returns 1 : No problem detected, game is ongoing, update both player, awating input from player 1
If it returns 2 : No problem detected, game is ongoing, update both player, awating input from player 2
If it returns 3 : The Command was not valid, most likely a problem from the front Command, the Client that sent the command should be deemed loser
If it returns 4 : The Command was supposedly valid, but it caused an error in intern, the game should be cancelled
If it returns 5 : The Code Crashed, the game should be cancelled, and the code fixed
If it returns 61 : Game is over, Player 1 won
If it returns 62 : Game is over, Player 2 won
If it returns 63 : Game is over, Ended in Draw

Potentially, Front can be AFK or Disconnect.
For AFK, IMO, back should run a 1 min timer, if timer is up, and no player sent command, back has to send me a command
I'll describe it farther bellow. Motor will then progress the game and re-send new game states to dispatch.
For Disconnect, I don't know if you want to handle the disconnection, best case scenario
At the end of timer, send me AFK command, repeat until there is a a reconnection or a winner
Easy way out, make the first disconnected player lose the game, and update him of the results when he reconnects for the first time

Let's consider also Back's handling of Motor.
Back shouldn't call again Motor function on a room XX if an other Motor is still working on room XX
In the case that Motor isn't responding and didn't answer anything, Back should terminate the process and the game should be cancelled

Back run motor with command to initiate a new game in the room XX
./motor.py XX I A1B C2D
I for initialisation
A is player 1, it's either P for real player or I for AI
C is player 2, it's either P for real player of I for AI
B is Deck 1 for Witcher deck, 2 for Wild-Hunt deck
D is Deck 1 for Witcher deck, 2 for Wild-Hunt deck
(If AI is implemented, it will be automatically Witcher Deck for starters)
XX : Number of the room from 00 to 99

From there, motor will create a fresh room file XXM.json that describes the game states for the motor
And it prepares a XX1.json that describes the game state and possible action and corresponding commands for P1 and XX2.json for P2
(If AI, Motor will always manage internally the AI)

Right after game initialization, Back send game stats to human player, there is a mulligan phase, all Human player receive a game state.
Front will send a command umber to the back.
When Back has received the command from all human players, Back runs this command :
./motor.py XX M 1xxxxxxxxx 2yyyyyy
XX is the number of the room
1 is player 1, 2 is player 2. 
xxxxxx and yyyy is ai if it's an ai
xxxxxx and yyyy otherwise is a command indicating the mulligan cards.
(If a player is an AI just send 0000 or 000000 for corresponding AI)

When the AFK timer times up, Back run the command
./motor.py XX T
XX is the number of the room
T is the letter T to indicated Time Up
Motor will then progress the game and update it

When front runs a command it will be a number, Back runs the command
./motor.py XX P abcde..
XX for the number of the room
P is the leter P to indicated Play
abcde.. it's the first command sent by a front


III)  Review of the Database the motor uses
All the cards are registered in a database called library.db for the motor.
It contains complete every pieces informations of every cards that the game posses
For a precise rundown, you can read Library_rm.md
The Goal is that when a player makes a command,
Motor updated the game_state, then at every step, check the Library to determine additionnal effects
And Recheck the Library to determine the next possible commands and write updated Game States


IV)   Review of how a motor game state is made
1) Code of a game states
Game has 2 Players : Player that starts , Player that plays second at start, indicates no player
Each player have different zones : Nowhere , Deck , Hand , Front Row , Back Row , Graveyard
Each Card can be at different position in those zones : 00 Nowhere, 01 = leftmost (Hand, Rows), or Bottom most (Deck Graveyard), incrementing
Each Card can have different ID and different states.
The differents ID are 1 or 2 for player 1 or player 2, followed by a number between 01 to 52 for specific card ID
The different states are : 
Boosted : true / false (if the card has Strength > Initial Value)
Hurt : true / false (if the card has Stregth < Initial Value)
Elixir_left : 2, 1 or 0 (0 if no Elixir in used, otherwise turn left before penality)
Revived : true or false (for cards that can comeback 1 time or stay on board 2 round)
So basically Each Zones are listed, in each Zone, all cards ID are listed in order
Row can also have state : Frost : Value (value is number of turn still active)
Player also have state :
Player : true or false, if it's AI or real player
Crown : 0, 1, 2 : How many crown the player has
Pass : true, false if the player has passed or not
Turn : true, false if it's the player turn or not
Num : If it's player 1 or Player 2

Card position in hand, in graveyard and on board don't really matter.
A position of a card is tracked so XXXX : Player (1 P1 2 P2) Zone (Out of game 0, Deck 1, Hand, 2, Front 3, Back 4, Graveyard 5)
Followed by their position XX starting from 01
_
Game also has states
Track Number of Cards in different zone for convenience
Track who is active player, what is his number, what is opponent number

Check motor_game_state_template for an idea

2) Initialisation of the motor game state
Simply randomize the decks specified by the command, and pull 10 cards
Then dispatch the Mulligan waiting

3) Update of a the motor game state
Apply the command received following VII) Procedure, then update the game state

V)    Review of how the motor determines the possible plays
Motor read motor game states.
It identifies whose player it's the turn.
Then it reads every card and every state.
For each card, check Library to determine if the card can be played and the conditions to be played
This is how a command code is made
First we identify where the action is coming from
Player        : 0 Not related to player, 1 Related to player playing first, 2 Related to player playing second
Action        : 0 Pass , 1 Give Up , 2 Power , 3 Play a card, 4 Target, 5 Mulligan, 6 Pass turn
Card ID       : 000 if not needed , ID otherwise 101 to 152 or 201 to 252
Zone From     : 0 Nowhere , 1 Deck , 2 Hand , 3 Front Row , 4 Back Row , 5 Graveyard, 6 Player, 7 Oponent
Position From : 00 Nowhere, 01 for Leftmost (Board Hand) or Bottom most (Deck Graveyard), incrementing
Played Zone   : 0 Nowhere , 1 Deck , 2 Hand , 3 Front Row , 4 Back Row , 5 Graveyard, 6 Player, 7 Oponent
Played Posit  : 00 Nowhere, 01 for Leftmost (Board Hand) or Bottom most (Deck Graveyard), incrementing
Target Zone   : 0 Nowhere , 1 Deck , 2 Hand , 3 Front Row , 4 Back Row , 5 Graveyard, 6 Player, 7 Oponent
Target Posit..:.00 Nowhere, 01 for Leftmost (Board Hand) or Bottom most (Deck Graveyard), incrementing
For Mulligan 15XXXXXXXXXX or 25YYYYYY, XXXXXXXXX and YYYYYY being the ID of the cards picked for muligan, 000 for not selecting a card.

Btw Auto Adding a card, will add on the right
If you play a card on position 2, it will become the new number 2, so old 2 becomes 3


VI)   Review of how a player game state is made
It copies the Game State for each player, but removes all secret data
It checks for all possible plays, and list them all.
Front should be able to translate those codes into possible actions for the user

VII)  Review of how the motor plays a turns out until next game state
First it verifies that the entered command is a command that was authorized in the game state sent.
Then it will execute the command step by step verifiying if conditions are mets that trigger new event.
For exemple Roach is played from the deck automatically if specific cards are played on the board.
Some cards will join graveyard if they lose strength.
Some cards will preserve the turn priority for the player

VIII) Review of how AI pickup its plays

Motor will Fork the game states for every possible Command up to 1 turn.
It will then calculate Score AI - Score Opponent on the Board
It will identify the highest gap in Score amonth all the Forks
Some cards may give additional value to add over the gap
If the higest gap is negative it will consider to pass, unless it leads to defeat
It will play the same play it did in the Fork in the actual game
All the remaining files will be discarded until AI is called again

IX)   Review of choices made, and logs for the creation of the game
- Project Started Early September
- We merged 2 binomes into a group of 4, Lucas+Nima and Quentin+Cyril
- Lucas wished for a Gwent game, a sub game we can play notably in The Witcher 3 but also as a standalone
- Nima wished for meetings and a locked project before forming it officially and preworking on back before that
- We had in important first meeting at 42 on 26/08/31, we studied subject and what modules we wanted to do
- We had a slower start, eventually at mid September this is how we progressed and how we delt the roles
- Lucas and Nima turned full focused into the back, Quentin focused into the front, I focused on the game
- 1st Half of September, I essentially locked the functionning of the game and the architectural logic between Front <-> Back <-> Game Motor
- 3rd Week of September, I definitely locked the rules and the Decklist, and the functionnal structure of the Motor.
Time was lost there through miscommunication
Back is really advanced, Front is fairly advanced, but requieres update from Motor to progress.
- 4th Week of September, my goal was to have a functionnal Motor, bare, but that is not too much spaghetti code so it can be upgraded.
Ideally 1st Week of October should be dedicated to AI, bug fixing, and Game Upgrade.

The difficulty to adapt Gwent, is that the initial Game in Withcher 3 is kind of boring imo, and more adapted for PC monitor rather than Phone Monitor.
There is a standalone game nowadays, adapted also for mobile, but on the opposite, it's extremely complex in terms of ruling.
My first objective was to get the best out of both and respecting these Criterias :
- Game must be fun
- Game must be balanced
- Game must not be too complex to code, ideally it should be upgradable, and be able to incorporate AI
- Game must clearly make you feel you are playing a Gwent game set in Witcher Universe
- Game can't really be Witcher 3 version or Gwent Modern for different reasons, an in between must be made
