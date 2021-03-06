"""A fun little program that can automatically run every x time frame that uses the SHiFT API to redeem keys.

Attributes:
    bSupportAllPlatforms (bool): Whether or not to support just *epic*
    debug (bool): Whether or not we want to print out all output
    platforms (list): A list of all supported platforms
    redeemedCodes (dict): A dictionary of previously redeemed keys, structure: {"keyString": "platform"}
    requestClient (TYPE): Just the current requests.session()
    shiftURL (str): A constant value of the base SHiFT url.
"""
import os
import re
import sys
import time
import json
import pickle
import getpass
import requests
import subprocess
from time import sleep
import browser_cookie3 as bc
from bs4 import BeautifulSoup

print("Running SHiFT Redeemer!")

# Windows: https://www.windowscentral.com/how-create-task-using-task-scheduler-command-prompt
# Linux: https://janakiev.com/blog/python-background/

# User settings / sessions
requestClient = requests.session()

debug = False # Just a statement for debug info in the future
bSupportAllPlatforms = False # Whether or not we should attempt to redeem keys for all of the platforms...
# Enabling this can potentially get you rate-limited which makes it quite hard

bContinueRedeeming = True # Whether or not we should keep redeeming our keys

# Our format for how the saved keys JSON should be stored
redeemedCodes = { "keys": [{"": ""}], "scheduled":False }

# Some constants just for ease / my memory
shiftURL = "https://shift.gearboxsoftware.com" # Just the base url for all of our requests
platforms = ["epic","steam","xbox","ps"] # A set of the possible? platforms for our keys

# All the bits of code for redeeming keys go here
# All of these functions are steps used in redeeming a key
def getRedemptionForm(key, platform):
	redemptionURL = "{}/code_redemptions/new".format(shiftURL)
	token = getCSRFToken(redemptionURL)
	if(debug): print("CSRF Token: {0}".format(token))
	response = requestClient.get("{shiftURL}/entitlement_offer_codes?code={code}".format(shiftURL=shiftURL, code=key), headers=
			{'x-csrf-token': token,
	            'x-requested-with': 'XMLHttpRequest'})
	if(debug): 
		print("getRedemptionForm: {0} | {1} | {2}".format(response.request.method, response.url, response.status_code))

	soup = BeautifulSoup(response.text, "html.parser")
	if not soup.find("form", class_="new_archway_code_redemption"):
		return False, response.status_code, response.text.strip()

	inputs = soup.find_all("input", attrs=dict(name="authenticity_token"))
	redemptionFormCodes = soup.find_all(id="archway_code_redemption_code")
	redemptionChecks = soup.find_all(id="archway_code_redemption_check")
	redemptionServices = soup.find_all(id="archway_code_redemption_service")
	validPlatform = False
	index = 0
	for i, s in enumerate(redemptionServices):
		if platform in s["value"]:
			index = i
			validPlatform = True
			break

	if not validPlatform:
		return False, response.status_code, "This code is not available for the platform specified"

	formData = {"authenticity_token": inputs[index]["value"],
		"archway_code_redemption[code]": redemptionFormCodes[index]["value"],
		"archway_code_redemption[check]": redemptionChecks[index]["value"],
		"archway_code_redemption[service]": redemptionServices[index]["value"]}
	return True, response.status_code, formData
def checkRedemptionStatus(response):
	if response.status_code == 302: return "redirect",  response.headers["location"]
	soup = BeautifulSoup(response.text, "lxml")
	div = soup.find("div", id="check_redemption_status")
	getStatus, url, fallback = None, None, None
	
	if div:
		getStatus = div.text.strip()
		url = div["data-url"]
		fallback = div["data-fallback-url"]

	if getStatus:
		token = getCSRFToken(response)
		count = 0
		while True:
			if count > 5:
				return "redirect", fallback
			newURL = "{}/{}".format(shiftURL, url)
			if(debug): print("	checkRedemptionStatus: GET " + newURL)
			rawJSON = requestClient.get(newURL, allow_redirects=False, headers={'x-csrf-token': token, 'x-requested-with': 'XMLHttpRequest'} )
			data = json.loads(rawJSON.text)
			if "text" in data:
				text = data["text"]
				if "success" in text.lower():
					return "success", text
				elif "failed" in text.lower():
					return "redeemed", text
				return None, text
			sleep(0.5)
			count += 1

	return None, None
def redeemForm(formData):
	redemptionURL = "{}/code_redemptions".format(shiftURL)
	response = requestClient.post(redemptionURL, data=formData, headers = {"Referer": "{}/new".format(redemptionURL)}, allow_redirects=False)

	if(debug): print("	redeemForm: {0} | {1} | {2}".format(response.request.method, response.url, response.status_code))

	status, redirect = checkRedemptionStatus(response)
	redemption = False
	# keep following redirects
	while status == "redirect":
		if "code_redemptions/" in redirect: redemption = True
		r2 = requestClient.get(redirect)
		status, redirect = checkRedemptionStatus(r2)
	if status == "redeeemed":
		status == "success"
		redirect = "Already Redeemed"
	elif not redemption or response.status_code == 429:
		status = "Try Later"
		redirect = "To redeem SHiFT codes, launch a SHiFT enabled game or wait an hour!"
	return status, redirect
# This function gets used for whenever we want to redeem a key (obviously)
# It takes in the key string, and the platform (relatively unused so far)
def redeemKey(key, platform):

	for keyRedeemed in redeemedCodes["keys"]:
		if key in keyRedeemed:
			if keyRedeemed[key] == platform:
				if(debug): print("Key already redeemed: {0} ({1})".format(key, platform))
				return "alreadyRedeemed"

	found, statusCode, formData = getRedemptionForm(key, platform) # Get our info back from the redemption form for whether or not its expired/available
	if(debug):  print("	redeemKey #1: {0} | {1} | {2}".format(found, statusCode, formData))
	# If we could actually find more info on the key, must've errored out
	if not found:
		if "expired" in formData: # If our code was expired, we should add it back to our JSON
			redeemedCodes["keys"].append({key : platform})
			with open("savedKeys.json", "w") as f:
				json.dump(redeemedCodes, f)
			return "Expired Code"
		if "not available" in formData or statusCode == 500: # If it wasn't available... it somehow made it into the list but we should still exlude it in the future
			redeemedCodes["keys"].append({key : platform})
			with open("savedKeys.json", "w") as f:
				json.dump(redeemedCodes, f)
			return "Invalid Code"
		print("Unknown error getting form data: ")
		print(formData)
		return "UNKNOWN ERROR"

	status, result = redeemForm(formData) # Here's where the proper key redemption happens
	if(debug): print(" redeemKey #2 (redeemForm): {0} | {1}".format(status, result))

	if status != "Try Later" or result == "Already Redeemed": # If we redeemed the key, should exclude it in the futre
		# Write out key to JSON since why redeem already redeemed keys.
		redeemedCodes["keys"].append({key : platform})
		with open("savedKeys.json", "w") as f: json.dump(redeemedCodes, f)
	if status == "Try Later": # If its "Try Later", that means we got rate limited...
		bContinueRedeeming = False
		return False

	print("Key successfully redeemed: {0}".format(key))
	return status == "success"

# This function is used at the very end, whenever we start to redeem all of our keys
def redeemAllKeys(keyJSON):	
	for shiftKey in keyJSON:
		if bContinueRedeeming:
			platform = shiftKey["platform"].lower()
			code = shiftKey["code"]
			if platform == "universal":
				if bSupportAllPlatforms:
					for platformCode in platforms:
						if redeemKey(code, platformCode) != "alreadyRedeemed":
							sleep(2.5)
					continue
				else:
					platform = "epic"
			elif platform == "playstation":
				platform = "ps"
			if redeemKey(code, platform) != "alreadyRedeemed":
				sleep(5)
		else:
			print("Rate limited! Please wait an hour or launch a SHiFT enabled title!")
			break

# Here's the bit of code used for logging in, so that way we can keep all of our stuff organized (somewhat)
def getCSRFToken(urlData):
	response = None
	if(type(urlData) == str):
		response = requestClient.get(urlData).text
	else:
		response = urlData.text
	csrfToken = re.search('csrf-token" content="(.*)"', response).group(0).split('content="')[1].replace('"','',1)
	return csrfToken

def login(username, password):
	csrfToken = getCSRFToken("{}/home".format(shiftURL))
	loginData = {"authenticity_token": csrfToken, "user[email]": username, "user[password]": password}
	response = requestClient.post("{}/sessions".format(shiftURL), data=loginData, headers={"Referer": "{}/home".format(shiftURL)})
	if(debug): 
		print("	Login: {0} | {1} | {2}".format(response.request.method, response.url, response.status_code))
	
	if("si" in requestClient.cookies):
		with open("loginInfo.cookie", "wb") as f:
			pickle.dump(requestClient.cookies, f)
		return True

	if("?redirect_to=false" in response.url):
		print("Try again... Incorrect login info!")
		return False
def infolessLogin():
	# Read out saved cookies so that way you don't have to login every time to run the program.
	if(os.path.exists("loginInfo.cookie")):
		print("Using cached login info...")
		with open("loginInfo.cookie", "rb") as f:
			requestClient.cookies.update(pickle.load(f))
	else:
		hasLoadedCookies = False

		if 'browser_cookie3' in sys.modules: # Probably best to check if the module is loaded eh?
			shiftCookies = None
			try: 
				print("(Attempting) to load chrome cookies...")
				shiftCookies = bc.chrome()
				print("Loaded chrome cookies...")
			except:
				print("(Attempting) to load firefox cookies...")
				shiftCookies = bc.firefox()
				print("Loaded firefox cookies...");
			if(shiftCookies != None):
				requestClient.cookies.update(shiftCookies)
			hasLoadedCookies = (shiftCookies != None)

		if not hasLoadedCookies: # If we weren't able to load our cookies, we should just prompt them for their input.
			bProperLoginInfo = False
			while not bProperLoginInfo:
				print("Login to your SHiFT account...")
				user = input("SHiFT Email: ")
				password = getpass.getpass(prompt="Password: ")
				bProperLoginInfo = login(user, password)

# All the bits useful for scheduling the tasks to auto run every 1hr
def scheduleTask():
	if os.name == 'nt': # Windows
		output, error = subprocess.Popen('SchTasks /Query /TN "SHiFT Automation"', stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		decodedError = error.decode("cp1251")
		# If it errors out we know that we don't have a scheduled task anymore.
		if "ERROR" in decodedError and "Access is denied" in decodedError:
			print("Access is denied. Please run as administrator...")
		elif "ERROR" in decodedError and not redeemedCodes["scheduled"]:
			bProperInfo = False

			while not bProperInfo:
				inputPrompt = input("Do you want to schedule this program to run every hour (Program will be hidden) (Y/N)? ")
				if inputPrompt == "Y" or inputPrompt == "y":
					bProperInfo = True
					redeemedCodes["scheduled"] = True
				elif inputPrompt == "N" or inputPrompt == "n":
					# If we said no, we should probably delete it if it exists in the first place.
					subprocess.Popen('SchTasks /Delete /TN "SHiFT Automation" /f', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					break

			if bProperInfo:
				properPath = os.path.realpath(__file__).replace(".py",".exe")
				# SchTasks /Create /SC HOURLY /TN "SHiFT Automation" /TR /NP "K:\Borderlands 3 - Tools\Auto SHiFT Redeemer (Background Process)\release\autoRedeemer.exe"
				properCommand = 'SchTasks /Create /SC HOURLY /TN "SHiFT Automation" /NP /TR "{0}"'.format(properPath)
				subprocess.Popen(properCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				# SchTasks /Delete /TN "SHiFT Automation"
				output, error = subprocess.Popen('SchTasks /Query /XML /TN "SHiFT Automation"', stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
				print(error)
				data = output.decode("cp1251").replace("<Hidden>false</Hidden>","<Hidden>true</Hidden>")
				fileIn = open("SHiFT Automation.xml","w+")
				fileIn.write(data)
				fileIn.close()
				subprocess.Popen('SchTasks /Delete /TN "SHiFT Automation" /f', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				subprocess.Popen('SchTasks /Create /XML "SHiFT Automation.xml" /TN "SHiFT Automation"').wait(timeout=1000)


infolessLogin() # Ask for login info, if we can't read it from other methods
scheduleTask() # Schedule our task to run it, if the user agrees with it

# Read out the keys from savedKeys.json
print("Reading cached keys...")
if(os.path.exists("savedKeys.json")): # Load the keys from the JSON, if it exists
	with open("savedKeys.json") as f: redeemedCodes = json.load(f)
else: # Write out the keys from the JSON using a saved setup
	with open("savedKeys.json", "w") as f: json.dump(redeemedCodes, f)


# Now we get key codes from https://shift.orcicorn.com
print("Using data provided by Orcicorn's SHiFT and VIP Code archive...")
keyJSON = json.loads(requestClient.get("https://shift.orcicorn.com/tags/borderlands3/index.json").text)[0]["codes"]

# Sometimes the file sticks around after a bit, so we should remove it right 'round here.
if os.path.exists("SHiFT Automation.xml"): os.remove("SHiFT Automation.xml")
print("Starting to redeem keys...")
# Start to redeem all of our keys
redeemAllKeys(keyJSON)

# Note that we've redeemed all the keys 
print("All known keys redeemed!")