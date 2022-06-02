import os
import time
import urllib.request as ul
import tkinter as tk
import threading
import shutil
import platform
import re
import traceback


if platform.system() == 'Windows':
	O_MARK = 'o'
	X_MARK = 'x'
else: # Darwin & Linux, far cuter
	O_MARK = '✓'
	X_MARK = '×'

DWN_ROOT = 'albums' # TODO: a better, customisable place, possibly let user choose
if not os.path.isdir(DWN_ROOT):
	os.mkdir(DWN_ROOT)
LOG = os.path.join(DWN_ROOT, 'buondua-downloader.log')
# minimum wait time between downloads per image (seconds),
# to prevent getting blocked from the website,
# EDIT AT YOUR OWN RISK!
WAIT_TIME = 3

# Don't add these exact addresses to queue
BLACKLIST = [
	'https://buondua.com/',
	'https://buondua.com/hot',
	'https://buondua.com/collection',
]

class Gui(tk.Frame):

	def __init__(self, master = None):
		tk.Frame.__init__(self, master)
		self.col_left = tk.Frame(master)
		self.col_right = tk.Frame(master)
		self.bot_left = tk.Frame(master)
		self.bot_right = tk.Frame(master)
		self.bot_sec_left = tk.Frame(master)
		self.bot_sec_right = tk.Frame(master)

		self.col_left.grid(row=0, column=0)
		self.col_right.grid(row=0, column=1)
		self.bot_left.grid(row=1, column=0)
		self.bot_right.grid(row=1, column=1)
		self.bot_sec_left.grid(row=2, column=0)
		self.bot_sec_right.grid(row=2, column=1)

		self.queue_list = []      # list of URLS
		self.queue_list_head = [] # header, titles only
		self.is_downloading = False
		self.done = 0   # '✓ %d'
		self.dusted = 0 # '× %d'

		self.add_elements()
		self.set_free_space()
		self.run_listener()

	def add_elements(self):
		"""Draw GUI elements."""
		self.output = tk.Text(self.col_left, width=50, height=30, wrap='word', state='disabled')
		# Tags for update_output(text, TAG)
		self.output.tag_configure('red', foreground='red')
		self.output.tag_configure('blue', foreground='blue')

		self.queue = tk.Text(self.col_right, width=30, height=30, wrap='none', state='disabled')
		self.current_title = tk.Label(self.bot_left, text='Waiting..')
		self.queue_progress = tk.Label(self.bot_right, text='0 / 0')
		self.free_space = tk.Label(self.bot_sec_left, text='Free: 0 GB')
		self.xo_progress = tk.Label(self.bot_sec_right, text='0 %s 0 %s' % (O_MARK, X_MARK))

		self.scroll_output = tk.Scrollbar(self.col_left, orient='vertical', command=self.output.yview)
		self.scroll_queue = tk.Scrollbar(self.col_right, orient='vertical', command=self.queue.yview)

		self.output.configure(yscrollcommand=self.scroll_output.set)
		self.queue.configure(yscrollcommand=self.scroll_queue.set)

		self.elements = [self.output, self.queue, self.current_title, self.queue_progress,
			self.free_space, self.xo_progress]
		# FIXME: currently only browsing for Windows
		if platform.system() == 'Windows':
			self.files_btn = tk.Button(self.bot_sec_left, text='Galleries', command=self.explore)
			self.elements.append(self.files_btn)
		self.scrolls = [self.scroll_output, self.scroll_queue]

		for el in self.elements:
			el.pack(side='left', pady=2, padx=1)
		for sc in self.scrolls:
			sc.pack(side='left', fill='y')

	def run_listener(self):
		"""Header function for periodic calls, gets recalled every 1s."""
		self.check_clipboard()
		self.check_queue_list()
		self.after(1000, self.run_listener)

	def update_gui(self):
		"""Update queue list and related GUI elements when a change occurs in queue elements."""
		self.queue.configure(state='normal')
		self.queue.delete('1.0', 'end')
		self.queue.insert('end', '\n'.join(self.queue_list_head))
		self.queue.configure(state='disabled')
		self.set_queue_progress()
		self.set_free_space()

	def update_output(self, text, tag = ''):
		"""Print out to view, mostly current progress.
		View gets cleared every 10000 characters.
		
		Keyword arguments:
		text -- value that gets appended to 'stdout'
		tag -- optional tag value for changing colours of the output
		"""
		self.output.configure(state='normal')
		if len(self.output.get('1.0', 'end')) >= 10000:
			self.output.delete('1.0', 'end')
			self.output.insert('end', 'Clearing the view..\n')
		self.output.insert('end', text, tag)
		self.output.see('end')
		self.output.configure(state='disabled')

	def check_queue_list(self):
		"""Begin a new download process if nothing is downloading & there are elements left in queue list.
		Gets called periodically in run_listener().
		"""
		if not self.is_downloading:
			if len(self.queue_list) > 0:
				self.is_downloading = True
				t = threading.Thread(target=self.start, args=(self.queue_list[0],))
				t.start()

	def check_clipboard(self):
		"""Check if a buondua URL is on clipboard & pass to add_to_queue().
		Don't accept the URLs in BLACKLIST, as well as pagination and tag addresses.
		Gets called periodically in run_listener().
		"""
		try:
			clip_val = self.clipboard_get()
			if (clip_val.startswith('https://buondua.com/')
			and not clip_val in BLACKLIST
			and not clip_val.startswith('https://buondua.com/?start=')
			and not clip_val.startswith('https://buondua.com/tag/')):
				self.add_to_queue(clip_val)
		except Exception:
			traceback.print_exc()

	def add_to_queue(self, clip_val):
		"""Add URL to queue list if it matches certain criteria:
		If queue list length is greater than 0 & same element doesn't exist, append it.
		Else, just append it.
		
		Keyword arguments:
		clip_val -- A buondua URL from the clipboard
		"""
		split_url = split_url_head(clip_val) # URL's last part for naming
		if len(self.queue_list_head) > 0:
			if (not split_url in self.queue_list_head
			and not ('%s ' % O_MARK + split_url) in self.queue_list_head
			and not ('%s ' % X_MARK + split_url) in self.queue_list_head):
				self.queue_list_head.insert(0, split_url)
				self.queue_list.append(clip_val)
				self.update_gui()
		else:
			self.queue_list_head.insert(0, split_url)
			self.queue_list.append(clip_val)
			self.update_gui()
	
	def set_title(self, val = ''):
		"""Set label of currently running job.
		
		Keyword arguments:
		val -- title of the current album (default '')
		"""
		if val == '':
			var = 'All complete!'
		else:
			var = val
			if len(var) > 48:
				var = val[:45] + '...'
		self.current_title.config(text=var)

	def set_queue_progress(self):
		"""Set label of queue & xo progress.
		Gets called on every queue list change in update_gui().
		Ex. output: 42 / 59 & 33 ✓ 9 ×
		Signifying: 42 out of 59 jobs are done. 33 successful, 9 skipped.
		"""
		progress = '%d / %d' % (abs(len(self.queue_list_head) - len(self.queue_list)), len(self.queue_list_head))
		xo_val = '%d %s %d %s' % (self.done, O_MARK, self.dusted, X_MARK)
		self.queue_progress.configure(text=progress)
		self.xo_progress.configure(text=xo_val)

	def set_free_space(self):
		"""Set label of remaining disk space in destination.
		Gets called on every queue list change in update_gui().
		"""
		total, used, free = shutil.disk_usage(DWN_ROOT)
		val = 'Free: %d GB' % (free // (2**30))
		self.free_space.configure(text=val)

	def explore(self):
		"""Browse into the downloads directory in the explorer."""
		os.startfile(DWN_ROOT)

	# --- core --- #
	def start(self, url):
		"""Check if a set with same header already exists & download if not.
		Only checks for the directory name and not individual images.
		
		Keyword arguments:
		url -- URL of a buondua set
		"""
		print(url)
		out = [] # list of image URLs
		album_name = split_url_head(url)
		magic_string = 'photo 1-0' # used for finding the first picture link

		# Connect and get the web page
		try:
			client = ul.urlopen(ul.Request(url, headers={'User-Agent': 'Mozilla/5.0'}))
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
			link_template = datasrc.replace('data-src=','').replace('\"', '').split('?')[0].replace('001.webp','%03d.webp').replace('001.jpeg','%03d.jpeg')

			# Get the album size from link
			album_size = int(srcline_split[srcline_split.index('photos)') - 1].replace('(',''))
			print(link_template)
			for x in range(1, album_size + 1):
				out.append(link_template % x)

			dest_dir = os.path.join(DWN_ROOT, album_name)
			try:
				if not os.path.exists(dest_dir):
					os.makedirs(dest_dir)
					self.download_images(out, dest_dir, album_name)
				else: # FIXME: maybe check for number of images rather than directory name to see if it exists
					self.update_output(album_name)
					self.update_output(' already exists.\n', 'blue')
					self.queue_list_head[self.queue_list_head.index(album_name)] = '%s ' % X_MARK + album_name
					self.dusted += 1
					del(self.queue_list[0])
					self.update_gui()
					self.is_downloading = False
			except OSError:
				traceback.print_exc()
				return

		except Exception as e:
			traceback.print_exc()
			# Skip download if an exception occurs during link conversion
			self.update_output('Error:', 'red')
			self.update_output(f' {e}\nSkipping {album_name}.\n')
			# Basically a copy of skipping if dir exists above
			self.queue_list_head[self.queue_list_head.index(album_name)] = '%s ' % X_MARK + album_name
			self.dusted += 1
			del(self.queue_list[0])
			self.update_gui()
			self.is_downloading = False

	def download_images(self, links, dest, header):
		"""Start downloading images and update the 'stdout' as it progresses.
		Output the time it took with set information to the log file when done.

		Keyword arguments:
		links -- list of image links from a URL
		dest -- destination directory path for the images
		header -- destination directory name, as well as part file name
		"""
		self.set_title(header)
		total_time = 0
		total_pauses = 0
		get_opener()
		self.update_output('Starting %s..\n' % header)
		for n, link in enumerate(links):
			try:
				name = f'{header}_{n+1}.jpg'
				self.update_output('Downloading %02d/%02d.. ' % ((n+1), len(links)))
				start = time.time()
				ul.urlretrieve(link, os.path.join(dest, name))
				end = time.time()
				passed = end - start
				total_time += passed
				self.update_output('Done. %.2f seconds.\n' % passed)

				if (n + 1) == len(links):
					pass
				elif passed < WAIT_TIME:
					add = WAIT_TIME - passed
					self.update_output('Waiting for additional %.2f seconds.\n' % add)
					time.sleep(add)
					total_pauses += add

			except Exception:
				traceback.print_exc()
			finally:
				continue

		stat = f'{time.strftime("%Y-%m-%d %H:%M:%S")}:: {header}: {len(links)} images, {(total_time / 60):.1f} min. downloading, {(total_pauses / 60):.1f} min. waiting ({((total_time + total_pauses) / 60):.1f} min. total).'
		statn = stat + '\n'
		self.update_output(statn)
		print(stat)
		with open(LOG, 'a') as l:
			l.write(statn)
		
		self.queue_list_head[self.queue_list_head.index(header)] = '%s ' % O_MARK + header
		self.done += 1
		del(self.queue_list[0])
		self.update_gui()
		self.is_downloading = False
		if len(self.queue_list) == 0:
			self.set_title()


def get_opener():
	"""Set request user-agent."""
	opener = ul.build_opener()
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36')]
	ul.install_opener(opener)

def split_url_head(url):
	"""Split URL by removing its body and last 3 sections for naming.
	e.g. https://buondua.com/youmi-vol-775-rena-70-photos-26165
	-> youmi-vol-775-rena

	Keyword arguments:
	url -- A URL to be converted into a name string
	"""
	split_url = '-'.join(url.split('/')[-1].split('-')[:-3])
	# somewhat of a solution to #13 on GitHub:
	# removes Eastern Characters from the URL,
	# or what they look like after getting copied
	split_url = re.sub('%..', '', split_url)
	if split_url.endswith('-'):
		split_url = split_url[:-1]
	return split_url

def get_geometry():
	"""Return geometry to spawn the program in the middle of the screen.
	Only in 1920px width.
	"""
	program_width = 690
	screen_width = 1920
	x_position = (screen_width - program_width) / 2
	return '%dx550+%d+30' % (program_width, x_position)

def start_gui():
	"""Launch GUI."""
	root = tk.Tk(className='buondua-downloader')
	root.title('buondua-downloader')
	root.geometry(get_geometry())
	app = Gui(master=root)
	app.mainloop()


if __name__ == '__main__':
	start_gui()
