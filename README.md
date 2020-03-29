# Borderlands 3 SHiFT Redeemer

A quick little tool to constantly run some code to redeem SHiFT codes for Borderlands 3!

This python code requests data from [Orcicorn's SHiFT JSON API](https://shift.orcicorn.com/tags/borderlands3/index.json) for a list of golden keys. 
It can be configurated to run every hour while hidden and attempt to redeem more codes from there.

# Installation

1. Download the exe available at [Releases](https://github.com/FromDarkHell/BL3ShiftRedeemer/releases/)
2. Run the exe, 
3. It'll probably take a bit to get started but: it'll first attempt to read your browser cookies for login info
	* If it can't read cookies, it'll prompt you for your SHiFT Email. Go ahead and fill it in
	* Next up, enter your password since it's kinda needed to login in
4. It'll prompt you if you want to run it every hour. (This feature only works on Windows so far)
    * It should hopefully say something along the lines of `SUCCESS: The scheduled task "SHiFT Automation" was created`. If it doesn't, please contact me for help!
        * If you plan to remove the self-scheduling in the future you can run `SchTasks /Delete /TN "SHiFT Automation" /f` in your terminal or you can run `Task Scheduler` and delete it from there.
5. Next it'll run through all of the codes, generating a list of all the ones that you've used, and if you've not used it, it'll activate it and then mark it as used!
6. That's it!
7. If you chose to automate execution, you'll need not touch SHiFT keys (probably) unless you want to!

# Credits

* [Orcicorn](https://twitter.com/orcicorn) for creating their wonderful [JSON api](https://shift.orcicorn.com/tags/borderlands3/index.json)
* [BrokenNoah](https://www.deviantart.com/brokennoah) for creating the cool free icons for [Borderlands 3](https://www.deviantart.com/brokennoah/art/Borderlands-3-icons-797030087)
* [trs](https://github.com/trs) for doing most of the programmatical heavy lifting with SHiFT at their [shift-code](https://github.com/trs/shift-code) repository.
* [Gearbox Software](https://www.gearboxsoftware.com/) obviously for creating BL3 and SHIFT
