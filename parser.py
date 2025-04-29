import requests
from bs4 import BeautifulSoup
import json

def search(searchTerm):
    searchURL = 'http://www.myinstants.com/search/?name=' + searchTerm

    r = requests.get(searchURL)
    soup = BeautifulSoup(r.text, 'html.parser')
    buttonList = []

    for link in soup.find_all("div", class_="instant"):
        buttonName = link.find("a", class_="instant-link").text.strip() if link.find("a", class_="instant-link") else "Unbekannt"

        smallButton = link.find("button", class_="small-button")
        if smallButton and 'onclick' in smallButton.attrs:
            s = smallButton['onclick']
            buttonUrl = s.partition("('")[-1].rpartition("')")[0]
            button = {
                "name": buttonName,
                "url": buttonUrl
            }
            buttonList.append(button)
        else:
            print(f"No 'small-button' or 'onclick'-Attribute found for: {buttonName}")

    return json.dumps(buttonList)

if __name__ == "__main__":
    print(search(input("Search for: ")))
