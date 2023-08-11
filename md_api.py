import requests
from datetime import datetime, timedelta

API_URL = "https://api.mangadex.org/"

class MangadexAPI:
	def __init__(self):
		self.session_token: str
		self.refresh_token: str
		self.session_expiration: datetime
	
	def login(self, user, password):
		self.parse_login_data(
			requests.post(
			API_URL + "/auth/login", json={
			"username": user,
			"password": password
			}, timeout=5
			).json()
		)
		return self.refresh_token
	
	def load_refresh_token(self, refresh_token):
		self.refresh_token = refresh_token
		self.refresh()
	
	def parse_login_data(self, data):
		tokens = data["token"]
		self.session_token = tokens["session"]
		self.refresh_token = tokens["refresh"]
		self.session_expiration = datetime.now() + timedelta(minutes=15)
	
	def refresh(self):
		self.parse_login_data(
			requests.post(API_URL + "/auth/refresh", json={
			"token": self.refresh_token
			}, timeout=5).json()
		)
	
	def request(self, method: str, endpoint: str, **kwargs):
		if datetime.now() > self.session_expiration:
			self.refresh()
		kwargs = {
			"method": method,
			"url": API_URL + endpoint.removeprefix("/"),
			"headers": {
			"Authorization": f"Bearer {self.session_token}",
			},
			"timeout": 5,
			**kwargs
		}
		resp = requests.request(**kwargs)
		return resp.json()
	
	def get(self, endpoint: str, params=None, **kwargs):
		kwargs = {"params": params, **kwargs}
		return self.request("GET", endpoint, **kwargs)
	
	def post(self, endpoint: str, json=None, **kwargs):
		kwargs = {"json": json, **kwargs}
		return self.request("POST", endpoint, **kwargs)
