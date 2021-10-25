import requests, json, random, csv, time
from threading import Thread, Lock
from datetime import datetime
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook, DiscordEmbed

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def string_builder(string, type):
    if type == "success":
        return '['+str(datetime.now()).split(' ')[1]+'] [AWLABCHECKER] ' + bcolors.OKGREEN + string + bcolors.ENDC
    elif type == "warning":
        return '['+str(datetime.now()).split(' ')[1]+'] [AWLABCHECKER] ' + bcolors.WARNING + string + bcolors.ENDC
    else:
        return '['+str(datetime.now()).split(' ')[1]+'] [AWLABCHECKER] ' + bcolors.FAIL + string + bcolors.ENDC


def load_proxies():

    proxies_vector = []

    with open("proxies.txt", 'r') as fp:
        all_proxies = fp.read().split('\n')

        if all_proxies == ['']:
            print(string_builder('No proxies found, running localhost..', 'warning'))
        else:
            for line in all_proxies:
                try:
                    proxy_parts = line.split(':')
                    ip, port, user, password = proxy_parts[0], proxy_parts[1], proxy_parts[2], proxy_parts[3]
                    tempProxy = {
                        'http': f'http://{user}:{password}@{ip}:{port}',
                        'https': f'http://{user}:{password}@{ip}:{port}'
                    }
                    proxies_vector.append(tempProxy)
                except:
                    pass

            print(string_builder('Loaded ' + str(len(proxies_vector)) + ' proxies.', 'warning'))
    
    return proxies_vector


class awlab_order_checker(Thread):

    headers = {
        'authority': 'www.aw-lab.com',
        'method': 'GET',
        'path': '/controllaspedizione',
        'scheme': 'https',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
    }

    headers_post = {
        'authority': 'www.aw-lab.com',
        'method': 'POST',
        'path': '/trackorder-result',
        'content-type': 'application/x-www-form-urlencoded',
        'scheme': 'https',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
    }

    writeMutex = Lock()
    webhookMutex = Lock()
    delay = 2
    webhook = "https://discord.com/api/webhooks/821454214240272384/oQtjciYP6sAvQgc2NorwSVrp9decsk75bBZj_eIQy57G6aiv-KR-A8xShhLNOlmvIPEe"
    url_get = "https://www.aw-lab.com/controllaspedizione"
    url_post = "https://www.aw-lab.com/trackorder-result"

    proxies_vector = load_proxies()

    def pick_proxy(self):
        index = random.randrange(len(awlab_order_checker.proxies_vector))
        self.proxy_to_use = awlab_order_checker.proxies_vector[index]
        self.session.proxies = self.proxy_to_use
        awlab_order_checker.proxies_vector.remove(self.proxy_to_use)

    def __init__(self, order_number, email, zipcode):
        Thread.__init__(self)
        self.order_number = order_number
        self.email = email
        self.zipcode = zipcode
        self.session = requests.session()

    def get_token(self):
        try:
            print(string_builder("[ORDER][" + self.order_number + '] CHECKING', 'warning'))
            if len(awlab_order_checker.proxies_vector) != 0:
                self.pick_proxy()
            r = self.session.get(awlab_order_checker.url_get, headers = awlab_order_checker.headers)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                self.crsf_token = soup.find('input',{'name':'csrf_token'})['value']
            else:
                print(string_builder("[ORDER][" + self.order_number + '] BANNED', 'failed'))
                time.sleep(awlab_order_checker.delay)
                self.get_token()
        except:
            print(string_builder("[ORDER][" + self.order_number + '] FAILED', 'failed'))
            time.sleep(awlab_order_checker.delay)
            self.get_token()

    def get_order_status(self):

        data = {
            'dwfrm_orderstatus_orderno_d0zhdvbjfxou': self.order_number,
            'dwfrm_orderstatus_email': self.email,
            'dwfrm_orderstatus_postal': self.zipcode,
            'dwfrm_orderstatus_search': 'Applica',
            'csrf_token': self.crsf_token 
        }

        try:
            r = self.session.post(awlab_order_checker.url_post, headers = awlab_order_checker.headers_post, data = data)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                self.order_status   = str(soup.find('div', {'class':'b-account-orders__status'}).text).strip()
                self.product_name   = str(soup.find('div', {'class':'b-product__name'}).text).strip()
                self.product_size   = str(soup.find('span', {'class':'b-product__value'}).text).strip()
                self.product_image  = str(soup.find('img', {'class':'js-image b-lazyload'})['data-lazy']).strip()

                if 'Fulfilled' in str(self.order_status):
                    self.tracking_number = soup.find('a', {'class':'b-account-orders__tracking-link'})['href']
                
                self.complete_task()
            else:
                print(string_builder("[ORDER][" + self.order_number + '] BANNED', 'failed'))
                time.sleep(awlab_order_checker.delay)
                if len(awlab_order_checker.proxies_vector) != 0:
                    self.pick_proxy()
                self.get_order_status()
        except:
            print(string_builder("[ORDER][" + self.order_number + '] FAILED', 'failed'))
            time.sleep(awlab_order_checker.delay)
            if len(awlab_order_checker.proxies_vector) != 0:
                self.pick_proxy()
            self.get_order_status()

    def complete_task(self):
        self.write_csv()
        self.send_webhook()
        print(string_builder("[ORDER][" + self.order_number + '] SAVED', 'success'))   

    
    def write_csv(self):
        awlab_order_checker.writeMutex.acquire()
        with open('awlab.csv', 'a', newline = '') as file:
            succesWriter = csv.writer(file)
            if 'Fulfilled' in str(self.order_status):
                succesWriter.writerow([self.order_number, self.product_name, self.product_size, self.order_status])
            else:
                succesWriter.writerow([self.order_number, self.product_name, self.product_size, self.order_status, self.tracking_number])
            
        awlab_order_checker.writeMutex.release()

    def send_webhook(self):
        awlab_order_checker.webhookMutex.acquire()

        temp_order = '||' + self.order_number + '||'
        temp_name = self.product_name
        temp_size = self.product_size
        temp_status = self.order_status
        embed = DiscordEmbed(title = 'AW-LAB ORDER CHECKER', color = 808080)
        embed.add_embed_field(name = 'ORDER', value = temp_order, inline = False)
        embed.add_embed_field(name = 'PRODUCT', value = temp_name, inline = True)
        embed.add_embed_field(name = 'SIZE', value = temp_size, inline = True)
        embed.add_embed_field(name = 'STATUS', value = temp_status, inline = False)
        embed.set_thumbnail(url = self.product_image)

        if 'Fulfilled' in str(self.order_status):
            temp_link = '||' + self.tracking_number + '||'
            embed.add_embed_field(name = 'TRACKING', value = temp_link, inline = True)
    
        #aggiungere logo footer
        embed.set_footer(text = 'COP HOUSE AWLAB ORDER CHECKER')

        webhook = DiscordWebhook(url = awlab_order_checker.webhook)
        webhook.add_embed(embed)

        try:
            webhook.execute()
        except:
            print(string_builder("[ORDER][" + self.order_number + '] WEBHOOK ERROR', 'failed'))

        awlab_order_checker.webhookMutex.release()
        

    def run(self):
        self.get_token()
        self.get_order_status()
