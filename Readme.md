GiantBomb Recommendation Web App
==================================

This is a Google Apps project that uses the Giant Bomb API to give Netflix-Style recommendations to giant bomb users based off of user ratings.
It uses a simple algorithm where it compares the given users ratings against other people who also rated the same games. 
The more similar their ratings are (i.e. if they both rated the same game with similar values and other games similar values) the higher weighting those users are given for recommendations.

Recommendations are simple the top x games that have high ratings from users with similar ratings (and have not already been rated by the user).
