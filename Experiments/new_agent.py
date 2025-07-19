problem = """
im having an issue with the agent game, right now when the user starts a chess game, here is a conversation history based on langsmith:
human
[User Name: Wissam]
Let's play chess

ai
Great! I've started a new chess game for you. Game ID: 40f9197d-f505-49b6-b862-af5828d0548f

It's your turn to move first (white pieces). You can make moves like 'e2e4' or 'd2d4' to start the game.

human
[User Name: Wissam]
e2e3

ai
```json
{
  "move": "d7d5",
  "fen": "rnbqkbnr/ppp1pppp/8/3p4/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
  "comment": "I played d7d5 to challenge the center."
}
```
1st issue: in the UI the agent response is blank. i think the front end is failing to extract the comment only and display it.

2nd issue: the agent chess parts are not moving in the chess board.

"""