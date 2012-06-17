#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from django.utils import simplejson

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.api import urlfetch
from google.appengine.api import memcache

from BeautifulSoup import BeautifulSoup

from google.appengine.runtime import DeadlineExceededError

import math
import os
import cgi
import logging

# Screen scrapes ratings from a users user reviews page on GB
def parseRatings(url):
	results = urlfetch.fetch(url)
	
	soup = BeautifulSoup(results.content)
	
	lastPage = True
	reviews = []
	
	paginator = soup.findAll(name='ul', attrs={"class" : "js-paginate-links paginate" })
	
	if len(paginator) != 0:
		lastResults = paginator[0].findAll(name='a', text='Last')
		lastPage = len(lastResults) == 0

	reviewUL = soup.findAll(name='ul', attrs={"class" : "list-objects"})[0]
	reviewLIs = reviewUL.findAll(name='li')
	
	logging.error(url)
	for reviewLI in reviewLIs:
		imgSpan = reviewLI.findAll(name='span', attrs={"class" : "img" })
	
		imgSrc = ""
		
		if(len(imgSpan) != 0):
			imgTag = imgSpan[0].findAll(name='img')
			imgSrc = imgTag[0]["src"]
			
		
		titleLinkRes = reviewLI.findAll(name='a', attrs={"class" : "name"});
		scoreImg = reviewLI.findAll(name='img', attrs={"class" : "rating-stars"})[0];
		
		if len(titleLinkRes) == 0:
			continue
		
		titleLink = titleLinkRes[0]
		if titleLink["href"].strip() == "" :
			continue
		
		id = titleLink["href"].split("/")[2][3:]
		score = scoreImg["src"].split("/")[-1].split("-")[-1][:-4]
		name = titleLink.contents[0]
		
		reviews.append((id, int(score), imgSrc, name))
	
	return lastPage, reviews
	
# Gets a users user reviews ratings from GB
def getUserRatings_(userName):
		
	baseUrl = "http://www.giantbomb.com/profile/" + userName + "/ratings/"
	
	allReviews = []
	
	lastUrl, reviews = parseRatings(baseUrl)
	allReviews = allReviews + reviews
	
	page = 2
	while not lastUrl:
		url = baseUrl + "?page=" + str(page)
		
		lastUrl, reviews = parseRatings(url)
		allReviews = allReviews + reviews
		
		page = page + 1
		
	return sorted(allReviews, key=lambda info: info[1], reverse=True)
	
# memcache wrapper for getUserRatings_
def getUserRatings(userName):

	data = memcache.get(userName)
	if data is not None:
		return data
	else:
		data = getUserRatings_(userName)
		memcache.add(userName, data, 1800)
		return data
	
api_key = "3c2be6c0f6d10150f5fb7227317816115c717938"
api_url = "http://api.giantbomb.com/"
api_user_reviews = api_url + "user_reviews/?api_key=" + api_key + "&format=xml&field_list=reviewer,score"

# Grabs the user reviews for a game (with the given game ID) and parses the results
# from the GB API, returning scores relative to user_score
def parseAPIRatings_(gameID, user_score):
	game_reviews_url = api_user_reviews + "&game=" + gameID
	
	results = urlfetch.fetch(game_reviews_url)
	soup = BeautifulSoup(results.content)
	
	error = soup.findAll(name='error')[0].contents[0]
	
	if error != 'OK':
		return False, []
	
	user_review_data = soup.findAll(name='user_review')
	
	scores = []
	
	for user_review in user_review_data:
		reviewer = user_review.findAll(name='reviewer')[0].contents[0]
		score = user_review.findAll(name='score')[0].contents[0]
		scores.append( (reviewer, int(score) - user_score) )
	
	return True, scores
		
# memcache wrapper for parseAPIRatings_
def parseAPIRatings(gameID, user_score):

	data = memcache.get(gameID + "_" + str(user_score))
	if data is not None:
		return True, eval(data)
	else:
		worked, data = parseAPIRatings_(gameID, user_score)
		
		if not worked:
			return worked, []
		
		memcache.add(gameID + "_" + str(user_score), str(data), 1800)
		return True, data
	
# Finds a set of game reccomendations for a give user
def findRecommendations(userID):
	# First grab all user reviews that the person with userID has made
	self_reviews = getUserRatings(userID) # 1 For loop
	
	logging.error(str(self_reviews))
	if len(self_reviews) == 0:
		raise NoUserReviewsException
	
	comparitive_reviews = []
	# Then grab all the API ratings for each of these games, calculate their differences
	for id, score, img, name in self_reviews: # 2 For Loops!
		api_res, scores = parseAPIRatings(id, score) # 1 For Loop
		
		if not api_res:
			continue

		comparitive_reviews.append(scores)

	user_rankings = { }
	# Coallate all the scores by userName, ignore any that is your own userID!
	for list in comparitive_reviews:
		for reviewer, comparitive_score in list:
			if reviewer == userID:
				continue
				
			if reviewer not in user_rankings:
				user_rankings[reviewer] = 0
				
			user_rankings[reviewer] = user_rankings[reviewer] + comparitive_score
			
			if reviewer in user_rankings: #this is repeat person, weight the score in their favor
				if user_rankings[reviewer] < 0:
					user_rankings[reviewer] = user_rankings[reviewer] + .25
				if user_rankings[reviewer] > 0:
					user_rankings[reviewer] = user_rankings[reviewer] - .25
	
		
	
	user_rankings_list = sorted(user_rankings.iteritems(), key= lambda x: 0 - math.fabs(x[1]) + (x[1] * 1/2), reverse=True)
	
	# Take the Top N reviewers, and examine each of their reviews of games
	num_top_viewers = 10
	
	top_users = user_rankings_list[:num_top_viewers]
	top_users_reviews = []
	
	for user, score in top_users:
		reviews = getUserRatings(user)
		top_users_reviews.append(reviews)
	
	recommended_games = {}
	# Among the Top N reviewers, find which games they have the most in common and report them as recommendations
	
	self_reviews_ids = [id for (id, rating, img, name) in self_reviews]
	for list in top_users_reviews:
		for game, score, img, name in list:
			if game in self_reviews_ids:
				continue
				
			if game not in recommended_games:
				recommended_games[game] = (0, img, name)
				
			recommended_games[game] = (recommended_games[game][0] + score, recommended_games[game][1], recommended_games[game][2])

	recommended_games = sorted(recommended_games.iteritems(), key= lambda x: x[1][0], reverse=True)
	
	return recommended_games

class NoUserReviewsException(Exception):
		pass

class MainHandler(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'index.html')
		f = open(path);
		self.response.out.write(f.read());
	
	def post(self):
	
		response = { 'error' : False, 'errtxt' : '', 'reccomends' : []}
		
		try:
			userName = cgi.escape(self.request.get('userName'))
				
			rankings = findRecommendations(userName)
			
			logging.error(str(rankings))
			for id, rank in rankings[:9]:
				#results = urlfetch.fetch(api_url + "game/" + id + "/?api_key=" + api_key + "&format=xml&field_list=name,image")
				#soup = BeautifulSoup(results.content)
				
				#game_names = soup.findAll('name')
				
				#game_name = "None"
				
				#if len(game_names) != 0:
				#	game_name = game_names[0].contents[0]
					
				#game_image = "None"
				
				#game_images = soup.findAll('thumb_url')
				
				#if len(game_images) != 0:
				#	game_image = game_images[0].contents[0]
					
				response["reccomends"].append( { "name" : rank[2], "image" : rank[1] } )
	
		except NoUserReviewsException, inst:
			response['error'] = True
			response['errtext'] = 'The user name you entered has no user reviews. Please make some and try again.'
			
		except DeadlineExceededError, inst:
			response['error'] = True
			response['errtext'] = "Oh no, It looks like the Google App Engine deadlines have been exceeded. Sorry, but due to running this on Google App Engine there are certain runtime limitations that I have to ahere to. If you run the query again it might successfully go through (due to caching), sorry for the inconvienence"

		except Exception, inst:
			response['error'] = True
			response['errtext'] = 'An Uknown Exception Has Occured. Server Says: ' + str(inst) + ". This can sometimes be caused by requests taking too long, if you try again it may work."
			
		self.response.out.write(simplejson.dumps(response));
		
def main():
	application = webapp.WSGIApplication([('/', MainHandler)],
											debug=True)
	util.run_wsgi_app(application)


if __name__ == '__main__':
	main()
