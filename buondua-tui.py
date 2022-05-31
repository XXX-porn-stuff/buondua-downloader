import os
import time
import argparse
import urllib.request as ul
from urllib.error import HTTPError


# minimum wait time between downloads per image (seconds),
# to prevent getting blocked from the website,
# EDIT AT YOUR OWN RISK!
WAIT_TIME = 3


def start():
	parser = argparse.ArgumentParser(description='Album downloader for buondua.com.')
	group_req = parser.add_argument_group('required arguments')

	group_req.add_argument('link', nargs='?',
		help='link of buondua.com album to download',
		type=str)

	args = parser.parse_args()
	if args.link is None:
		print('usage: buondua.py https://buondua.com/xxx-album-link-xxx')
		return
	out = []

	# Use additional album_name constructed by the link
	album_name = ''

	magic_string = 'photo 1-0' # used for finding the first picture link

	# Connect and get the web page
	try:
		client = ul.urlopen(ul.Request(args.link, headers={'User-Agent': 'Mozilla/5.0'}))
		htmllines = client.read().decode().split('\n')
		client.close()

		srcline = ''
		for each_line in htmllines: # search for the first picture link
			if magic_string in each_line:
				srcline = each_line
				break

		srcline_split = srcline.split(' ') # split for better manipulation
		datasrc = ''.join([x if 'data-src=' in x else '' for x in srcline_split]) # delete other parts except the part containing the pic download link

		# Construct link template
		link_template = datasrc.replace('data-src=','').replace('\"', '').split('?')[0].replace('001.jpg','%03d.jpg').replace('001.jpeg','%03d.jpeg').replace('001.webp','%03d.webp')

		# Get the album size from link
		album_size = int( srcline_split[srcline_split.index('photos)') - 1].replace('(',''))
		print(link_template)
		for x in range(1, album_size+1):
			out.append(link_template % x)
			album_name = link_template.split('/')[-1]
			album_name = album_name[: album_name.find('MrCong.com') - 1]


		path = f'albums/{album_name}/'
		try:
			if not os.path.exists(path):
				os.makedirs(path)
		except OSError as e:
			print(f'OSError: {e}')
			return

		download_images(out, path)
	except Exception as e:
		print(f'Error: {e}')

def get_opener():
	"""Set request user-agent."""
	opener = ul.build_opener()
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36')]
	ul.install_opener(opener)

def download_images(links, path):
	"""Start downloading images.

	Keyword arguments:
	links -- list of image links from a URL
	path -- destination directory path for the images
	"""
	total_time = 0
	total_pauses = 0
	get_opener()
	for n, link in enumerate(links):
		try:
			name = link.split('/')[-1].split('-')[-1]
			print('Downloading %s.' % link)
			start = time.time()
			ul.urlretrieve(link, path + name)
			end = time.time()
			passed = end - start
			total_time += passed
			print('Complete. Took %.2f seconds.' % passed)

			if (n + 1) == len(links):
				pass
			elif passed < WAIT_TIME:
				add = WAIT_TIME - passed
				print('Waiting for an additional %.2f seconds.' % add)
				time.sleep(add)
				total_pauses += add

		except HTTPError as e:
			print(f'\033[91mError: {e}\033[0m')
		finally:
			pass


	print(f'---\nDownloading {len(links)} images took {(total_time / 60):.1f} minutes ({total_time:.2f} seconds) to complete.\n  Plus {(total_pauses / 60):.1f} additional minutes ({total_pauses:.2f} seconds) of wait time.\n  {((total_time + total_pauses) / 60):.1f} minutes ({(total_time + total_pauses):.2f} seconds) in total.')


if __name__ == '__main__':
	start()
