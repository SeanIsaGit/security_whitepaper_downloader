from bs4 import BeautifulSoup as bs
import requests
import os
import PaperClip
import time


class PaperCut:

    def __init__(self):
        self.setup_details = PaperClip.read_json("news_paper.config")
        self.main_dl_path = self.setup_details['setup']['main_dl_path']
        self.vendor_list = []
        self.vendor_paths = {}
        self.doc_types = self.setup_details['setup']['doc_types']
        self.current_wp_vend = None
        self.wp_links_dict = {}
        self.vendor_new_files_dict = {}
        self.wp_links_file = self.setup_details['setup']['wp_links_file']
        self.new_links_file = self.setup_details['setup']['new_links_file']
        self.undownloadable_wp = {}
        self.undownloadable_wp_file = self.setup_details['setup']['undown_links_file']

    @staticmethod
    def _download_wp(url, path_to):
        local_filename = url.split('/')[-1]
        r = requests.get(url, stream=True)
        directory = os.path.dirname(path_to)
        if not os.path.exists(directory):
            os.makedirs(directory)
            print("Creating: " + directory)
        full_path = path_to + "/" + local_filename
        print("Downloading", local_filename)
        with open(full_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush() commented by recommendation from J.F.Sebastian

            return local_filename

    def _wp_already_dl(self, url, vendor_name):
        for root, dirnames, filenames in os.walk(self.main_dl_path + "/" + vendor_name):
            for fil in filenames:
                # using 'in' and not '==' as filename may have had other info appended during creation
                if url.split('/')[-1] in fil:
                    return True

        return False

    def _create_dirs(self):
        for vendor in self.vendor_list:
            if not os.path.exists(self.main_dl_path + "/" + vendor):
                print("Creating Dir ", end='')
                os.makedirs(self.main_dl_path + "/" + vendor)

            self.vendor_paths[vendor] = self.main_dl_path + "/" + vendor
            # print(self.main_dl_path + "/" + vendor)

    def _call_wp_funcs(self):
        for vendor_name in self.vendor_list:
            print("Grabbing links for {}".format(vendor_name))
            self.current_wp_vend = vendor_name
            eval('self.wp_{}()'.format(self.current_wp_vend))

    def grab_wp_links(self, vendor_list=None):
        if vendor_list is None:
            print("Using default vendor list for downloading...")
            self.vendor_list = self.setup_details['setup']['vendor_list']
        else:
            self.vendor_list = vendor_list
        for item in self.vendor_list:
            self.vendor_new_files_dict[item] = {
                "filenames": [],
                "urls": []
            }
        self._create_dirs()
        self._call_wp_funcs()
        self._write_links_to_json(self.wp_links_file)

    def _write_links_to_json(self, output_file):
        PaperClip.write_json(self.wp_links_dict, output_file)

    def _write_new_links_to_json(self, output_file):
        PaperClip.write_json(self.vendor_new_files_dict, output_file)

    def _write_undownloadable_links_to_json(self, output_file):
        PaperClip.write_json(self.undownloadable_wp, output_file)

    def _append_new_files_to_dict(self, url):
        self.vendor_new_files_dict[self.current_wp_vend]['filenames'].append(url.split('/')[-1])
        self.vendor_new_files_dict[self.current_wp_vend]['urls'].append(url)

    def download(self):
        for vendor in self.vendor_list:
            path = self.main_dl_path + "/" + vendor
            # only download if there are links to the dictionary
            if len(self.wp_links_dict) > 0:
                if vendor in self.wp_links_dict.keys():
                    for wp_url in self.wp_links_dict[vendor]:
                        if not self._wp_already_dl(wp_url, vendor):
                            time.sleep(.5)
                            self._download_wp(wp_url, path)
                            self._append_new_files_to_dict(wp_url)
                        else:
                            # TODO: Implement logging
                            print("Not downloading {} as already in {}".format(wp_url.split('/')[-1], path))
            undown_file = PaperClip.read_json(self.undownloadable_wp_file)
            if vendor in self.undownloadable_wp.keys():
                for wp_url in self.undownloadable_wp[vendor]:
                    print("Found undownloadable paper: ", wp_url)
                    if vendor in undown_file.keys():
                        if wp_url not in undown_file[vendor]:
                            print("New undownloadable paper found from {}: ".format(vendor), wp_url)
                            self._append_new_files_to_dict(wp_url)
            else:
                print("No links to download")

        self._write_undownloadable_links_to_json(self.undownloadable_wp_file)
        self._write_new_links_to_json(self.new_links_file)

    #################################################
    # Functions to grab individual vendor whitepapers
    #################################################

    def wp_bitdefender(self):
        wp_links = []
        undownloadable_list = []
        website_link = self.setup_details['setup']['vendor_urls'][self.current_wp_vend]

        page = requests.get(website_link)
        soup = bs(page.content, 'html.parser')
        wp_div = soup.find_all('div', {'class': "col-md-12 text-left stripe stripeGrey"})

        # get all wp links and append them to the wp_links list
        for items in wp_div:
            link_div = items.find_all('div', {'class': "col-md-3"})
            for link in link_div[0].find_all('a'):
                href = link.get('href')
                if href.endswith(tuple(self.doc_types)):
                    wp_links.append('https:' + href)
                    print("Got link: {}".format('https:' + href))
                else:
                    # if any of the links are not downloadable (ie: need to subscribe to see pdfs) append to list
                    undownloadable_list.append(link.get('href'))
                    print("Got link: {}".format('https:' + href))

        self.undownloadable_wp[self.current_wp_vend] = undownloadable_list

        # append the wp_links list to dictionary with vendor as key
        self.wp_links_dict[self.current_wp_vend] = wp_links

    def wp_symantec(self):
        undownloadable_list = []
        wp_links = []

        website_link = self.setup_details['setup']['vendor_urls'][self.current_wp_vend]
        page = requests.get(website_link)
        soup = bs(page.content, 'html.parser')

        # getting the sections for the current and archive years
        current_wp_section = soup.find_all('section', {
            'id': "contentsymantecenglishensecuritycenterwhitepapersjcrcontentbodyparsyscustomstackingcolumn"})
        archive_wp_section = soup.find_all('section', {
            'id': "contentsymantecenglishensecuritycenterwhitepapersjcrcontentbodyparsyscustomstackingcolumn0"})

        # getting the accordions for the current years and the archive years
        current_years = current_wp_section[0].find_all('section', {'class': "accordion-section"})
        archive_years = archive_wp_section[0].find_all('section', {'class': "accordion-section"})
        all_years = current_years + archive_years

        for i in range(len(all_years)):
            # current year in unicode
            # current_year = all_years[i].find('a', {'class': 'accordion-section-title'}).get_text().strip()
            for li in all_years[i].find_all('li'):
                href = li.find('a').get('href')
                if href.endswith(tuple(self.doc_types)):
                    wp_links.append('https://www.symantec.com:' + href)
                    print("Got link: {}".format('https://www.symantec.com:' + href))
                else:
                    # if any of the links are not downloadable (ie: need to subscribe to see pdfs) append to list
                    undownloadable_list.append(href)
                    print("Got link: {}".format('https://www.symantec.com:' + href))

        self.undownloadable_wp[self.current_wp_vend] = undownloadable_list
        self.wp_links_dict[self.current_wp_vend] = wp_links

    def wp_mcafee(self):
        wp_links = []
        undownloadable_list = []
        # had to use the chrome dev tools and watched the 'network' tab to see which url the aspx was using to
        # pageinate the results
        website_link = self.setup_details['setup']['vendor_urls'][self.current_wp_vend]
        for i in range(1, 50):
            page = requests.get(website_link.format(i))
            soup = bs(page.content, 'html.parser')
            resource_list = soup.find('resourcelist')
            resources = resource_list.find('resources')

            if len(resources) == 0:
                break

            for resource in resources:
                if resource.get('language-mfe') == "en":
                    href = resource.get('path')
                    if href.endswith(tuple(self.doc_types)):
                        wp_links.append('https://www.mcafee.com/uk' + '/' + href)
                        print("Got link: {}".format('https://www.mcafee.com/uk' + '/' + href))
                    else:
                        undownloadable_list.append('https://www.mcafee.com/uk' + '/' + href)
                        print("Got link: {}".format('https://www.mcafee.com/uk' + '/' + href))

            time.sleep(.1)
        self.undownloadable_wp[self.current_wp_vend] = undownloadable_list
        self.wp_links_dict[self.current_wp_vend] = wp_links

    def wp_trend_micro(self):
        wp_links = []

        website_link = self.setup_details['setup']['vendor_urls'][self.current_wp_vend]
        page = requests.get(website_link)
        soup = bs(page.content, 'html.parser')
        archive = soup.find('aside', {'id': 'archives-2'})
        month_links = archive.find_all('a')
        for month in month_links:
            month_page = requests.get(month.get('href'))
            month_soup = bs(month_page.content, 'html.parser')
            a = month_soup.find_all('a')
            hrefs = [link.get('href') for link in a]

            wp_links_cache = [href for href in hrefs
                              if href.endswith(tuple(self.doc_types))
                              and "http" in href]
            for link in wp_links_cache:
                print("Got link: {}".format(link))
            wp_links += wp_links_cache
            time.sleep(.25)

        wp_links = list(set(wp_links))
        self.wp_links_dict[self.current_wp_vend] = wp_links

    def wp_avast(self):
        undownloadable_list = []

        website_link = self.setup_details['setup']['vendor_urls'][self.current_wp_vend]
        page = requests.get(website_link)
        soup = bs(page.content, 'html.parser')

        resources = soup.find_all('div', {'class': 'resources-box all whitepaper'})
        for resource in resources:
            for a in resource.find_all('a'):
                href = a.get('href')
                undownloadable_list.append(href)
                print("Got link: {}".format(href))

        undownloadable_list = list(set(undownloadable_list))
        self.undownloadable_wp[self.current_wp_vend] = undownloadable_list

    def wp_eset(self):
        wp_links = []
        undownloadable_list = []

        website_link = self.setup_details['setup']['vendor_urls'][self.current_wp_vend]
        page = requests.get(website_link)
        soup = bs(page.content, 'html.parser')

        article_list = soup.find('ul', {'class': 'article-list skin-content-browser'})
        articles = article_list.find_all('li', {'class': 'item item-article without-media'})

        page_nav = soup.find('div', {'class': 'page-navigation'})
        last_page = page_nav.find('li', {'class': 'last'}).find('a').get('href').split('/')[-2]

        links = ["https://www.eset.com" + a.get('href') for article in articles for a in article.find_all('a')]

        for i in range(2, int(last_page) + 1):
            next_page_link = website_link + "/page/{}".format(i)
            next_page = requests.get(next_page_link)
            next_soup = bs(next_page.content, 'html.parser')
            article_list = next_soup.find('ul', {'class': 'article-list skin-content-browser'})
            articles = article_list.find_all('li', {'class': 'item item-article without-media'})

            links += ["https://www.eset.com" + a.get('href') for article in articles for a in article.find_all('a')]

        for link in links:
            pdf_page = requests.get(link)
            pdf_soup = bs(pdf_page.content, 'html.parser')

            content = \
                pdf_soup.find('div', {'class': 'col col-sm-9 article-content'}).find('div', {'class': 'csc-default'})

            try:
                href = content.find('a').get('href')
                if href.endswith(tuple(self.doc_types)):
                    print("Got link: {}".format(href))
                    wp_links.append(href)
                else:
                    undownloadable_list.append(href)
                    print("Got link: {}".format(href))
            except AttributeError as e:
                print('Couldn\'t find a pdf link: ', e)
            except BaseException as e:
                print('An exception occurred while visiting {}: {}'.format(link, e))

        undownloadable_list = list(set(undownloadable_list))
        self.undownloadable_wp[self.current_wp_vend] = undownloadable_list
        wp_links = list(set(wp_links))
        self.wp_links_dict[self.current_wp_vend] = wp_links
