####################################################################################################
#                                                                                                  #
#                                   KissNetwork Plex Channel                                       #
#                                                                                                  #
####################################################################################################
# import Shared Service Code
Domain				= SharedCodeService.domain
Headers				= SharedCodeService.kissheaders.Headers
Common				= SharedCodeService.common
Metadata			= SharedCodeService.metadata
KData				= SharedCodeService.data.Data
kissanimesolver		= SharedCodeService.kissanimesolver

# set global variables needed for imported packages
TITLE				= Common.TITLE
PREFIX				= Common.PREFIX
TIMEOUT				= Common.TIMEOUT
GIT_REPO			= 'Twoure/{}.bundle'.format(TITLE)
URL_CACHE_DIR		= 'DataHTTP'
THUMB_CACHE_DIR		= 'DataCovers'
BOOKMARK_CACHE_DIR	= 'DataBookmarks'

# setup Updater and update headers if Dict['init_run'] updates
from pluginupdateservice import PluginUpdateService
Updater = PluginUpdateService()
if not Updater.initial_run:
	Log("* Sending request to initialize headers")
	Thread.Create(Headers.init_headers, init=True)

# import local and remote packages
import messages
import requests
import time, re
from io import open
import rhtml as RHTML
from AuthTools import CheckAdmin
from DumbTools import DumbKeyboard, DumbPrefs
from DevTools import add_dev_tools, SaveCoverImage, SetUpCFTest, ClearCache, BookmarkTools

# more global variables
SORT_OPT = {'Alphabetical': '', 'Popularity': '/MostPopular', 'Latest Update': '/LatestUpdate', 'Newest': '/Newest'}
ADULT_LIST = set(['Adult', 'Smut', 'Ecchi', 'Lolicon', 'Mature', 'Yaoi', 'Yuri'])
CP_DATE = ['Plex for Android', 'Plex for iOS', 'Plex Home Theater', 'OpenPHT']
CFTest_KEY					= 'Manga'
RE_TITLE_CLEAN				= Regex(r'[^a-zA-Z0-9 \n]')
RE_TITLE_CLEAN_DOT			= Regex(r'[^a-zA-Z0-9 \n\.]')

# Set background art and icon defaults
# KissAnime
ANIME_ART					= 'art-anime.jpg'
ANIME_ICON					= 'icon-anime.png'
# KissAsian
ASIAN_ART					= 'art-drama.jpg'
ASIAN_ICON					= 'icon-drama.png'
# KissCartoon
CARTOON_ART					= 'art-cartoon.jpg'
CARTOON_ICON				= 'icon-cartoon.png'
# KissManga
MANGA_ART					= 'art-manga.jpg'
MANGA_ICON					= 'icon-manga.png'
# ReadComincOnline
COMIC_ART					= 'art-comic.jpg'
COMIC_ICON					= 'icon-comic.png'
# General
MAIN_ART					= 'art-main.jpg'
MAIN_ICON					= 'icon-default.png'
NEXT_ICON					= 'icon-next.png'
CATEGORY_VIDEO_ICON			= 'icon-video.png'
CATEGORY_PICTURE_ICON		= 'icon-pictures.png'
BOOKMARK_ICON				= 'icon-bookmark.png'
BOOKMARK_ADD_ICON			= 'icon-add-bookmark.png'
BOOKMARK_REMOVE_ICON		= 'icon-remove-bookmark.png'
BOOKMARK_CLEAR_ICON			= 'icon-clear-bookmarks.png'
SEARCH_ICON					= 'icon-search.png'
PREFS_ICON					= 'icon-prefs.png'
CACHE_COVER_ICON			= 'icon-cache-cover.png'
ABOUT_ICON					= 'icon-about.png'

MC = messages.NewMessageContainer(PREFIX, TITLE)

####################################################################################################
def Start():
	ObjectContainer.art = R(MAIN_ART)
	ObjectContainer.title1 = TITLE

	DirectoryObject.thumb = R(MAIN_ICON)
	DirectoryObject.art = R(MAIN_ART)
	PopupDirectoryObject.art = R(MAIN_ART)

	InputDirectoryObject.art = R(MAIN_ART)

	HTTP.CacheTime = 0
	HTTP.Headers['User-Agent'] = Common.USER_AGENT
	version = get_channel_version()

	Log.Debug('*' * 80)
	Log.Debug('* Platform.OS			= {}'.format(Platform.OS))
	Log.Debug('* Platform.OSVersion		= {}'.format(Platform.OSVersion))
	Log.Debug('* Platform.CPU			= {}'.format(Platform.CPU))
	Log.Debug('* Platform.ServerVersion	= {}'.format(Platform.ServerVersion))
	Log.Debug('* Channel.Version		= {}'.format(version))
	Log.Debug('*' * 80)

	# setup test for cfscrape
	SetUpCFTest(CFTest_KEY)

	# setup auto-managed bookmark backups
	BookmarkTools.auto_backup()

	# Clear Old Cached URLs & Cover Thumbs
	Thread.Create(ClearCache, itemname=URL_CACHE_DIR, timeout=TIMEOUT)
	Thread.Create(ClearCache, itemname=THUMB_CACHE_DIR, timeout=Datetime.Delta(weeks=4))

	# remove/clear old style of caching prior to v1.2.7
	if Dict['current_ch_version']:
		if Common.ParseVersion(Dict['current_ch_version']) < (1, 2, 7):
			Log(u"* Channel updated from {} to {}. Clearing old cache and moving Bookmark backups.".format(Dict['current_ch_version'], version))
			from DevTools import ClearOldCache, MoveOldBookmarks
			Thread.Create(MoveOldBookmarks)
			Thread.Create(ClearOldCache, itempath=Core.storage.join_path(Core.bundle_path, 'Contents', 'Resources'))
			Thread.Create(ClearOldCache, itempath=Core.storage.join_path(Core.storage.data_path, 'DataItems'))
		elif Common.ParseVersion(Dict['current_ch_version']) < Common.ParseVersion(version):
			Log(u"* Channel updated from {} to {}".format(Dict['current_ch_version'], version))

	# setup current channel version
	Dict['current_ch_version'] = version

####################################################################################################
@handler(PREFIX, TITLE, MAIN_ICON, MAIN_ART)
def MainMenu():
	"""Create the Main Menu"""
	#Thread.Create(kissanimesolver.test)
	
	Log.Debug('*' * 80)
	Log.Debug('* Client.Product		 = {}'.format(Client.Product))
	Log.Debug('* Client.Platform		= {}'.format(Client.Platform))
	Log.Debug('* Client.Version		 = {}'.format(Client.Version))

	# if cfscrape failed then stop the channel, and return error message.
	SetUpCFTest(CFTest_KEY)
	if not Dict['cfscrape_test']:
		return MC.message_container('Error',
			'CloudFlare bypass failed. Please report Error to Twoure with channel Log files.')
	elif not Headers.init_headers():
		return MC.message_container('Warning', 'Please wait while channel caches headers.  Exit channel and try again later.')

	admin = CheckAdmin()
	oc = ObjectContainer(title2=TITLE, no_cache=Client.Product in ['Plex Web'])

	cp_match = True if Client.Platform in Common.LIST_VIEW_CLIENTS else False

	data = list()
	for t, u in Common.BaseURLListTuple():
		thumb = 'icon-{}.png'.format(t.lower())
		rthumb = None if cp_match else R(thumb)
		art = 'art-{}.jpg'.format(t.lower())
		rart = R(art)
		prefs_name = 'kissasian' if t == 'Drama' else 'kiss{}'.format(t.lower())
		data.append({
			'prefs_name': prefs_name, 'title': t, 'art': art,
			'rart': rart, 'thumb': thumb, 'rthumb': rthumb, 'url': u
			})

	# set thumbs based on client
	if cp_match:
		bookmark_thumb = None
		prefs_thumb = None
		search_thumb = None
		about_thumb = None
	else:
		bookmark_thumb = R(BOOKMARK_ICON)
		prefs_thumb = R(PREFS_ICON)
		search_thumb = R(SEARCH_ICON)
		about_thumb = R(ABOUT_ICON)

	# set status for bookmark sub menu
	if Dict['Bookmark_Deleted']:
		if Dict['Bookmark_Deleted']['bool']:
			Dict['Bookmark_Deleted'].update({'bool': False, 'type_title': None})
			Dict.Save()
	else:
		Dict['Bookmark_Deleted'] = {'bool': False, 'type_title': None}
		Dict.Save()

	status = Dict['Bookmark_Deleted']
	Dict.Save()

	if admin:
		if Prefs['update_channel'] == 'Stable':
			# Setup Updater to track latest release
			Updater.gui_update(
				PREFIX + '/updater', oc, GIT_REPO,
				tag='latest', list_view_clients=Common.LIST_VIEW_CLIENTS
				)
		else:
			# Setup Updater to track branch commits
			Updater.gui_update(
				PREFIX + '/updater', oc, GIT_REPO,
				branch='dev', list_view_clients=Common.LIST_VIEW_CLIENTS
				)

	# set up Main Menu depending on what sites are picked in the Prefs menu
	prefs_names = ['kissanime', 'kissasian', 'kisscartoon', 'kissmanga', 'kisscomic']
	b_prefs_names = [p for p in prefs_names if Prefs[p]]
	# present KissMain directly if no other sites selected
	if len(b_prefs_names) == 1:
		b_prefs_name = b_prefs_names[0]
		p_data = [d for d in data if d['prefs_name'] == b_prefs_name][0]
		if Prefs['simple']:
			oc.add(DirectoryObject(
				key=Callback(KissMain, url=p_data['url'], title=p_data['title'], art=p_data['art']),
				title=p_data['title'], thumb=p_data['rthumb'], art=p_data['rart']
				))
		else:
			KissMain(url=p_data['url'], title=p_data['title'], art=p_data['art'], ob=False, oc=oc)
	else:
		for d in Util.ListSortedByKey(data, 'title'):
			if Prefs[d['prefs_name']]:
				oc.add(DirectoryObject(
					key=Callback(KissMain, url=d['url'], title=d['title'], art=d['art']),
					title=d['title'], thumb=d['rthumb'], art=d['rart']
					))

	oc.add(DirectoryObject(
		key=Callback(BookmarksMain, title='My Bookmarks', status=status), title='My Bookmarks',
		thumb=bookmark_thumb
		))

	if Client.Product in DumbPrefs.clients:
		DumbPrefs(PREFIX, oc, title='Preferences', thumb=prefs_thumb)
	elif admin:
		oc.add(PrefsObject(title='Preferences', thumb=prefs_thumb))

	oc.add(DirectoryObject(key=Callback(About), title='About / Help', thumb=about_thumb))

	if Client.Product in DumbKeyboard.clients:
		DumbKeyboard(PREFIX, oc, Search, dktitle='Search', dkthumb=R(SEARCH_ICON))
	else:
		oc.add(InputDirectoryObject(
			key=Callback(Search), title='Search', prompt='Search for...', thumb=search_thumb
			))

	return oc

####################################################################################################
@route(PREFIX + '/kissmain', ob=bool)
def KissMain(url, title, art, ob=True, oc=None):
	"""Create All Kiss Site Menu"""

	if ob:
		oc = ObjectContainer(title2=title, art=R(art))
	if Prefs['simple']:
		return DirectoryList(page=1, pname='All', category='All', base_url=url, type_title=title, art=art)

	newest_c_title = 'New {}'.format(title)

	oc.add(DirectoryObject(
		key=Callback(DirectoryList,
			page=1, pname='All', category='All', base_url=url, type_title=title, art=art),
		title='All'))
	oc.add(DirectoryObject(
		key=Callback(AlphabetList, url=url, title=title, art=art), title='Alphabets'))
	oc.add(DirectoryObject(
		key=Callback(GenreList, url=url, title=title, art=art), title='Genres'))

	if title == 'Drama':
		oc.add(DirectoryObject(
			key=Callback(CountryList, url=url, title=title, art=art), title='Countries'))

	if (title == 'Anime') or (title == 'Cartoon') or (title == 'Drama'):
		oc.add(DirectoryObject(
			key=Callback(DirectoryList,
				page=1, pname='/Genre/Movie', category='Movie', base_url=url, type_title=title, art=art),
			title='Movies'))

	oc.add(DirectoryObject(key=Callback(StatusList, url=url, type_title=title, art=art),
		title='Status'))

	if (title == 'Drama') or (title == 'Cartoon') or (title == 'Comic'):
		oc.add(DirectoryObject(key=Callback(TopList, url=url, type_title=title, art=art),
			title='Top'))

	oc.add(DirectoryObject(
		key=Callback(DirectoryList,
			page=1, pname='/LatestUpdate', category='Latest Update', base_url=url, type_title=title, art=art),
		title='Latest Update'))

	if title == 'Anime':
		newest_c_title = 'Recent Additions'
		oc.add(DirectoryObject(
			key=Callback(DirectoryList,
				page=1, pname='/NewAndHot', category='New & Hot', base_url=url, type_title=title, art=art),
			title='New & Hot'))

	oc.add(DirectoryObject(
		key=Callback(DirectoryList,
			page=1, pname='/Newest', category=newest_c_title, base_url=url, type_title=title, art=art),
		title=newest_c_title))
	oc.add(DirectoryObject(
		key=Callback(DirectoryList,
			page=1, pname='/MostPopular', category='Most Popular', base_url=url, type_title=title, art=art),
		title='Most Popular'))

	if ob:
		return oc

####################################################################################################
@route(PREFIX + '/status-list')
def StatusList(type_title, url, art):
	"""
	Setup Status List for each site
	Ongoing and Completed list
	"""

	oc = ObjectContainer(title2=type_title, art=R(art))
	for s in ['Ongoing', 'Completed']:
		oc.add(DirectoryObject(
			key=Callback(DirectoryList,
				page=1, pname='/Status/{}'.format(s), category=s, base_url=url, type_title=type_title, art=art),
			title=s))
	return oc

####################################################################################################
@route(PREFIX + '/top-list')
def TopList(type_title, url, art):
	"""
	Setup Top list for Cartoon and Drama
	Top Today, Week, Month
	"""

	oc = ObjectContainer(title2=type_title, art=R(art))
	for t in ['Top Day', 'Top Week', 'Top Month']:
		tab = t.split('Top')[1].strip().lower()
		oc.add(DirectoryObject(
			key=Callback(HomePageList,
				tab=tab, category=t, base_url=url, type_title=type_title, art=art),
			title=t))
	return oc

####################################################################################################
@route(PREFIX + '/about')
def About():
	"""
	Return Resource Directory Size, and KissNetwork's Current Channel Version
	Includes Developer Tools Menu if enabled within prefs and current user is admin
	"""

	oc = ObjectContainer(title2='About / Help')

	# Get Resources Directory Size
	d = GetDirSize(Core.storage.data_item_path(THUMB_CACHE_DIR))

	if Prefs['devtools'] and CheckAdmin():
		add_dev_tools(oc)

	oc.add(DirectoryObject(key=Callback(About),
		title='Version {}'.format(get_channel_version()), summary='Current Channel Version'))
	oc.add(DirectoryObject(key=Callback(About),
		title='N/A | Still Removing Files' if d == 'Error' else d,
		summary='Number of Images Cached | Total Images Cached Size'))

	return oc

####################################################################################################
def get_channel_version():
	plist = Plist.ObjectFromString(Core.storage.load(Core.plist_path))
	return plist['CFBundleVersion'] if 'CFBundleVersion' in plist.keys() else 'Current'

####################################################################################################
@route(PREFIX + '/validateprefs')
def ValidatePrefs():
	"""check prefs, placeholder for now"""

####################################################################################################
@route(PREFIX + '/bookmarks', status=dict)
def BookmarksMain(title, status):
	"""Create Bookmark Main Menu"""

	if (status['bool']) and (Client.Platform not in ['Plex Home Theater', 'OpenPHT']):
		oc = ObjectContainer(title2=title, header="My Bookmarks",
			message='{} bookmarks have been cleared.'.format(status['type_title']), no_cache=True)
	else:
		oc = ObjectContainer(title2=title, no_cache=True)

	# check for 'Bookmarks' section in Dict
	if not Dict['Bookmarks']:
		# if no 'Bookmarks' section the return pop up
		return MC.message_container(title,
			'No Bookmarks yet. Get out there and start adding some!!!')
	# create boomark directory based on category
	else:
		key_list = sorted(Dict['Bookmarks'].keys())
		# return bookmark list directly if only one kiss site selected in prefs
		bm_prefs_names = [('kissasian' if m == 'Drama' else 'kiss{}'.format(m.lower())) for m in key_list]
		bool_prefs_names = [p for p in bm_prefs_names if Prefs[p]]
		if len(bool_prefs_names) == 1:
			b_prefs_name = bool_prefs_names[0].split('kiss')[1].title()
			b_prefs_name = 'Drama' if b_prefs_name == 'Asian' else b_prefs_name
			if b_prefs_name in key_list:
				art = 'art-{}.jpg'.format(b_prefs_name.lower())
				return BookmarksSub(b_prefs_name, art)
		# list categories in bookmarks dictionary that are selected in prefs
		for key in key_list:
			prefs_name = 'kissasian' if key == 'Drama' else 'kiss{}'.format(key.lower())
			art = 'art-{}.jpg'.format(key.lower())
			thumb = 'icon-{}.png'.format(key.lower())

			# if site in Prefs then add its bookmark section
			if Prefs[prefs_name]:
				# Create sub Categories for Anime, Cartoon, Drama, and Manga
				oc.add(DirectoryObject(
					key=Callback(BookmarksSub, type_title=key, art=art),
					title=key, thumb=R(thumb), summary='Display {} Bookmarks'.format(key), art=R(art)))

		# test if no sites are picked in the Prefs
		if len(oc) > 0:
			# hide/unhide clear bookmarks option, from DevTools
			if not Prefs['hide_clear_bookmarks']:
				# add a way to clear the entire bookmarks list, i.e. start fresh
				oc.add(DirectoryObject(
					key=Callback(ClearBookmarks, type_title='All'),
					title='Clear All Bookmarks?',
					thumb=R(BOOKMARK_CLEAR_ICON), art=R(art),
					summary='CAUTION! This will clear your entire bookmark list, even those hidden!'))

			return oc
		else:
			# Give error message
			return MC.message_container('Error',
				'At least one source must be selected in Preferences to view Bookmarks')

####################################################################################################
@route(PREFIX + '/bookmarkssub')
def BookmarksSub(type_title, art):
	"""Load Bookmarked items from Dict"""

	if not type_title in Dict['Bookmarks'].keys():
		return MC.message_container('Error',
			'{} Bookmarks list is dirty. Use About/Help > Dev Tools > Bookmark Tools > Reset {} Bookmarks'.format(type_title, type_title))

	oc = ObjectContainer(title2='My Bookmarks | {}'.format(type_title), art=R(art))

	# Fill in DirectoryObject information from the bookmark list
	# create empty list for testing covers
	for bookmark in Util.ListSortedByKey(Dict['Bookmarks'][type_title], type_title):
		item_title = bookmark['item_title']
		summary = bookmark['summary']
		summary2 = Common.StringCode(string=summary, code='decode') if summary else None

		cover_file = Common.CorrectCoverImage(bookmark['cover_file']) if bookmark['cover_file'] else None
		cover_url = Common.CorrectCoverImage(bookmark['cover_url']) if bookmark['cover_url'] else None

		cover = None
		if cover_file and cover_url:
			cover = Callback(GetThumb, cover_url=cover_url, cover_file=cover_file)

		item_info = {
			'item_sys_name': bookmark[type_title],
			'item_title': item_title,
			'short_summary': summary,
			'cover_url': cover_url,
			'cover_file': cover_file,
			'type_title': type_title,
			'base_url': Common.GetBaseURL(bookmark['page_url']),
			'page_url': Common.GetBaseURL(bookmark['page_url']) + '/' + bookmark['page_url'].split('/', 3)[3],
			'art': art}

		# get genre info, provide legacy support for older Bookmarks
		#   by updating
		force_update_cover = False
		if 'genres' in bookmark.keys():
			genres = [g.replace('_', ' ') for g in bookmark['genres'].split()]
			update = False
			if cover_url and Common.is_kiss_url(cover_url):
				cover_type_title = Common.GetTypeTitle(cover_url)
				cover_base_url = Common.RE_BASE_URL.search(bookmark['cover_url']).group(1)
				if 'date_added' not in bookmark.keys():
					Log.Debug("* Bookmark 'date_added' missing. Updating Bookmark Metadata.")
					update = True
					force_update_cover = cover_type_title == 'Anime'
				elif (cover_type_title, cover_base_url) not in Common.BaseURLListTuple():
					Log.Debug('* Bookmark Cover URL Domain changed. Updating Bookmark Metadata.')
					update = True
			else:
				page_base_url = Common.RE_BASE_URL.search(bookmark['page_url']).group(1)
				if (type_title, page_base_url) not in Common.BaseURLListTuple():
					Log.Debug('* Bookmark Page URL Domain changed. Updating Bookmark Metadata.')
					update = True
			if update:
				bm_info = item_info.copy()
				bm_info.update({'type_title': type_title, 'genres': bookmark['genres']})
				if 'date_added' in bookmark.keys():
					bm_info.update({'date_added': bookmark['date_added']})
				ftimer = float(Util.RandomInt(0,30)) + Util.Random()
				Thread.CreateTimer(interval=ftimer, f=UpdateLegacyBookmark, bm_info=bm_info, new_cover=force_update_cover)
		else:
			bm_info = item_info.copy()
			bm_info.update({'type_title': type_title})
			ftimer = float(Util.RandomInt(0,30)) + Util.Random()
			Thread.CreateTimer(interval=ftimer, f=UpdateLegacyBookmark, bm_info=bm_info)
			genres = ['Temp']

		if not Prefs['adult']:
			matching_list = set(genres) & ADULT_LIST
			if len(matching_list) > 0:
				continue

		oc.add(DirectoryObject(
			key=Callback(ItemPage, item_info=item_info),
			title=Common.StringCode(string=item_title, code='decode'),
			summary=summary2, thumb=cover, art=cover))

	if not Prefs['hide_clear_bookmarks']:
		# add a way to clear this bookmark section and start fresh
		oc.add(DirectoryObject(
			key=Callback(ClearBookmarks, type_title=type_title),
			title='Clear All \"{}\" Bookmarks?'.format(type_title),
			thumb=R(BOOKMARK_CLEAR_ICON), art=R(art),
			summary='CAUTION! This will clear your entire \"{}\" bookmark section!'.format(type_title)))

	return oc

####################################################################################################
@route(PREFIX + '/alphabets')
def AlphabetList(url, title, art):
	"""Create ABC Directory for each kiss site"""

	oc = ObjectContainer(title2='{} By #, A-Z'.format(title), art=R(art))
	for pname in list('#'+String.UPPERCASE):
		oc.add(DirectoryObject(
			key=Callback(DirectoryList,
				page=1, pname=pname.lower() if not pname == '#' else '0',
				category=pname, base_url=url, type_title=title, art=art),
			title=pname))
	Logger('* Built #, A-Z... Directories')
	return oc

####################################################################################################
@route(PREFIX + '/genres')
def GenreList(url, title, art):
	"""Create Genre Directory for each kiss site"""

	genre_url = url + '/{}List'.format(title)
	html = RHTML.ElementFromURL(genre_url)

	oc = ObjectContainer(title2='{} By Genres'.format(title), art=R(art))

	# Generate Valid Genres based on Prefs['adult']
	for genre in html.xpath('//div[@class="barContent"]//a'):
		genre_href = genre.get('href')
		if 'Genre' in genre_href and not 'Movie' in genre_href:
			if (Prefs['adult'] == False) and (genre_href.replace('/Genre/', '') in ADULT_LIST):
				continue
			# name used for title2
			category = html.xpath('//div[@class="barContent"]//a[@href="{}"]/text()'.format(genre_href))[0].replace('\n', '').strip()

			oc.add(DirectoryObject(
				key=Callback(DirectoryList,
					page=1, pname=genre_href, category=category, base_url=url, type_title=title, art=art),
				title=category))

	return oc

####################################################################################################
@route(PREFIX + '/countries')
def CountryList(url, title, art):
	"""Create Country Directory for KissAsian"""

	country_url = url + '/DramaList'  # setup url for finding current Country list
	html = RHTML.ElementFromURL(country_url)

	oc = ObjectContainer(title2='Drama By Country', art=R(art))

	# For loop to pull out valid Countries
	for country in html.xpath('//div[@class="barContent"]//a'):
		if "Country" in country.get('href'):
			pname = country.get('href')  # name used internally
			category = country.text.replace('\n', '').strip()  # name used for title2

			oc.add(DirectoryObject(
				key=Callback(DirectoryList,
					page=1, pname=pname, category=category, base_url=url, type_title=title, art=art),
				title=category))

	return oc

####################################################################################################
@route(PREFIX + '/directory')
def DirectoryList(page, pname, category, base_url, type_title, art):
	"""
	GenreList, AlphabetList, CountryList, and Search are sent here
	Pulls out Items name and creates directories for them
	Might to add section that detects if Genre is empty
	"""

	# Define url based on genre, abc, or search
	if "Search" in pname:
		item_url = base_url
		Logger('* Searching for \"{}\"'.format(category))
	# New & Hot list is only on Anime site, but made it uniform just in case
	elif pname == '/NewAndHot':
		item_url = base_url + '/{}List{}'.format(type_title, pname)
	# list from the front page, not effected by Prefs
	elif pname == '/LatestUpdate' or pname == '/Newest' or pname == '/MostPopular':
		item_url = base_url + '/{}List{}?page={}'.format(type_title, pname, page)
	# Sort order 'A-Z'
	elif SORT_OPT[Prefs['sort_opt']] is None:
		if ('Genre' in pname or 'Country' in pname
			or 'Ongoing' in pname or 'Completed' in pname):
			# Genre, Country, Ongoing, or Completed Specific
			item_url = base_url + '{}?page={}'.format(pname, page)
		elif "All" in pname:
			# All list
			item_url = base_url + '/{}List?page={}'.format(type_title, page)
		else:
			# No Genre, Country, Ongoing, or Completed
			item_url = base_url + '/{}List?c={}&page={}'.format(type_title, pname, page)
	# Sort order for all options except 'A-Z'
	elif ('Genre' in pname or 'Country' in pname
		or 'Ongoing' in pname or 'Completed' in pname):
		# Specific with Prefs
		item_url = base_url + '{}{}?page={}'.format(pname, SORT_OPT[Prefs['sort_opt']], page)
	elif "All" in pname:
		item_url = base_url + '/{}List{}?page={}'.format(type_title, SORT_OPT[Prefs['sort_opt']], page)
	else:
		# No Genre with Prefs
		item_url = base_url + '/{}List{}?c={}&page={}'.format(type_title, SORT_OPT[Prefs['sort_opt']], pname, page)

	Logger(u"* Sorting Option = '{}'".format(SORT_OPT[Prefs['sort_opt']]))  # Log Pref being used
	Logger(u"* Category = '{}' | URL = '{}'".format(pname, item_url))

	html = RHTML.ElementFromURL(item_url)

	pages = "Last Page"
	nextpg_node = None

	# determine if 'next page' is used in directory page
	if "Search" in pname:
		# The Search result page returnes a long list with no 'next page' option
		# set url back to base url
		base_url = Common.GetBaseURL(item_url)
		Logger("* Searching for {}".format(category))  # check to make sure its searching
	else:
		# parse html for 'last' and 'next' page numbers
		for node in html.xpath('///div[@class="pagination pagination-left"]//li/a'):
			if "Last" in node.text:
				pages = str(node.get('href'))  # pull out last page if not on it
			elif "Next" in node.text:
				nextpg_node = str(node.get('href'))  # pull out next page if exist

	# Create title2 to include directory and page numbers
	if not "Last" in pages:
		total_pages = pages.split('page=')[1]
		# set title2 ie main_title
		main_title = '{} | {} | Page {} of {}'.format(type_title, category, page, total_pages)
	elif "Search" in pname:
		# set title2 for search page
		main_title = 'Search for: {} in {}'.format(category, type_title)
	else:
		# set title2 for last page
		main_title = '{} | {} | Page {}, Last Page'.format(type_title, category, page)

	oc = ObjectContainer(title2=main_title, art=R(art))

	# parse url for each Item and pull out its title, summary, and cover image
	# took some time to figure out how to get the javascript info
	listing = html.xpath('//table[@class="listing"]//td[@title]')
	if not listing:
		listing = html.xpath('//div[@class="item"]')

	drama_test = type_title == 'Drama' and ('Search' not in pname)
	listing_count = len(listing)
	allowed_count = 200
	Logger('* {} items in Directory List.'.format(listing_count), kind='Info')
	if listing_count > allowed_count and 'Search' in pname:
		return MC.message_container('Error',
			'{} found.  Directory can only list up to {} items.  Please narrow your Search Criteria.'.format(listing_count, allowed_count))

	for item in listing:
		if not drama_test:
			title_html = HTML.ElementFromString(item.get('title'))
		else:
			title_html = item
			drama_title_html = HTML.ElementFromString(item.get('title'))
		try:
			if not drama_test:
				thumb = Common.CorrectCoverImage(item.xpath('./a/img/@src')[0])
				if 'http' not in thumb:
					thumb = base_url + thumb
			else:
				thumb = Common.CorrectCoverImage(item.xpath('./a/img/@src')[0])
			if not 'http' in thumb:
				Log.Debug('* thumb missing valid url. | {}'.format(thumb))
				Log.Debug('* thumb xpath = {}'.format(title_html.xpath('//img/@src')))
				Log.Debug('* item name | {} | {}'.format(title_html.xpath('//a/@href'), title_html.xpath('//a/text()')))
				thumb = None
				cover_file = None
			elif Common.is_kiss_url(thumb):
				cover_file = thumb.rsplit('/')[-1]
			else:
				cover_file = thumb.split('/', 3)[3].replace('/', '_')
		except Exception as e:
			Log(e)
			thumb = None
			cover_file = None

		if not drama_test:
			summary = title_html.xpath('//p/text()')[0].strip()
		else:
			summary = drama_title_html.xpath('//p[@class="description"]/text()')[0].strip()

		a_node = item.xpath('./a')[0]

		item_url_base = a_node.get('href')
		item_sys_name = Common.StringCode(string=item_url_base.rsplit('/')[-1].strip(), code='encode')
		item_url_final = base_url + Common.StringCode(string=item_url_base, code='encode')
		Logger('*' * 80)
		Logger('* item_url_base	 = {}'.format(item_url_base))
		Logger('* item_sys_name	 = {}'.format(item_sys_name))
		Logger('* item_url_final	= {}'.format(item_url_final))
		Logger('* thumb			 = {}'.format(thumb))

		item_title = None
		try:
			if not drama_test:
				item_title = a_node.xpath('./span[@class="title"]/text()')[0].strip()
			else:
				item_title = a_node.xpath('./span[@class="title"]/text()')[0].strip()
		except:
			pass
			
		item_title = item_title if item_title != None else item_sys_name
			
		Logger('* item_title	 = {}'.format(item_title))
			
		if 'Movie' in pname:
			title2 = item_title
		else:
			item_title_cleaned = RE_TITLE_CLEAN.sub('', item_title)

			try:
				if not drama_test:
					latest = item.xpath('./following-sibling::td')[0].text_content().strip().replace(item_title_cleaned, '')
				else:
					try:
						latest = item.xpath('./div[@class="ep-bg"]/a')[0].text_content()
					except:
						latest = drama_title_html.xpath('./p')[1].text_content().split(' ')[1]
						
				latest = latest.replace('Read Online', '').replace('Watch Online', '').lstrip('_').strip()
			except:
				latest = ''
			
			Log("latest: %s" % latest)
			
			if 'Completed' in latest:
				title2 = u'{} | {} Completed'.format(item_title, type_title)
			elif 'Not yet aired' in latest:
				title2 = u'{} | Not Yet Aired'.format(item_title)
			else:
				title2 = u'{} | Latest {}'.format(item_title, latest)

		item_info = {
			'item_sys_name': item_sys_name,
			'item_title': Common.StringCode(string=item_title, code='encode'),
			'short_summary': Common.StringCode(string=summary, code='encode'),
			'cover_url': thumb,
			'cover_file': cover_file,
			'type_title': type_title,
			'base_url': base_url,
			'page_url': item_url_final,
			'art': art
			}

		# if thumb is hosted on kiss site then cache locally if Prefs Cache all covers
		cover = Callback(GetThumb, cover_url=thumb, cover_file=cover_file)

		oc.add(DirectoryObject(
			key=Callback(ItemPage, item_info=item_info),
			title=title2, summary=summary, thumb=cover, art=cover))

	if nextpg_node:  # if not 'None' then find the next page and create a button
		nextpg = int(nextpg_node.split('page=')[1])
		Logger('* NextPage		  = {}'.format(nextpg))
		Logger('* base url		  = {}'.format(base_url))
		oc.add(NextPageObject(
			key=Callback(DirectoryList,
				page=nextpg, pname=pname, category=category,
				base_url=base_url, type_title=type_title, art=art),
			title='Next Page>>', thumb=R(NEXT_ICON)))

	if len(oc) > 0:
		Dict.Save()
		return oc
	return MC.message_container(type_title, '{} list is empty'.format(category))

####################################################################################################
@route(PREFIX + '/homedirectorylist')
def HomePageList(tab, category, base_url, type_title, art):
	"""
	KissCartoon, KissAsian, and ReadComicOnline have 'Top' list on home page.
	This returns those list.
	"""

	main_title = u'{} | {}'.format(type_title, category)
	oc = ObjectContainer(title2=main_title, art=R(art))

	html = RHTML.ElementFromURL(base_url)

	# scrape home page for Top (Day, Week, and Month) list
	for node in html.xpath('//div[@id="tab-top-{}"]/div'.format(tab)):
		page_node = Common.StringCode(string=node.xpath('./a')[1].get('href'), code='encode')
		item_sys_name = Common.StringCode(string=page_node.split('/')[-1], code='encode')
		item_title = node.xpath('./a/span/text()')[0]
		latest = node.xpath('./p/span[@class="info"][text()="Latest:"]/../a/text()')[0]
		title2 = u'{} | Latest {}'.format(item_title, latest)
		summary = 'NA'  # no summarys are given in the 'Top' lists
		try:
			thumb = Common.CorrectCoverImage(node.xpath('./a/img/@src')[0].get('src'))
			if not 'http' in thumb:
				thumb = None
				cover_file = None
			elif Common.is_kiss_url(thumb):
				cover_file = thumb.rsplit('/')[-1]
			else:
				cover_file = thumb.split('/', 3)[3].replace('/', '_')
		except:
			thumb = None
			cover_file = None
		page_url = base_url + (page_node if page_node.startswith('/') else '/' + page_node)

		item_info = {
			'item_sys_name': item_sys_name,
			'item_title': Common.StringCode(string=item_title, code='encode'),
			'short_summary': summary,
			'cover_url': thumb,
			'cover_file': cover_file,
			'type_title': type_title,
			'base_url': base_url,
			'page_url': page_url,
			'art': art
			}
		cover = Callback(GetThumb, cover_url=thumb, cover_file=cover_file)

		# send results to ItemPage
		oc.add(DirectoryObject(
			key=Callback(ItemPage, item_info=item_info), title=title2, thumb=cover, art=cover))

	Dict.Save()

	return oc

####################################################################################################
@route(PREFIX + '/item', item_info=dict)
def ItemPage(item_info):
	"""Create the Media Page with the Video(s)/Chapter(s) section and a Bookmark option Add/Remove"""

	# set variables
	item_sys_name = item_info['item_sys_name']
	item_title = item_info['item_title']
	type_title = item_info['type_title']
	base_url = item_info['base_url']
	page_url = item_info['page_url']
	art = item_info['art']

	# decode string & set title2 for oc
	item_title_decode = unicode(Common.StringCode(string=item_title, code='decode'))
	title2 = u'{} | {}'.format(type_title, item_title_decode)
	oc = ObjectContainer(title2=title2, art=R(art))

	html = RHTML.ElementFromURL(page_url)
	genres, genres_list = Metadata.GetGenres(html)

	if not Prefs['adult']:
		# Check for Adult content, block if Prefs set.
		genres = html.xpath('//p[span[@class="info"]="Genres:"]/a/text()')
		Logger('* genres = {}'.format(genres))
		if genres:
			matching_list = set(genres) & ADULT_LIST
			if len(matching_list) > 0:
				warning_string = ', '.join(list(matching_list))
				Logger('* Adult Content Blocked: {}'.format(warning_string), force=True, kind='Info')
				Logger('*' * 80)
				return MC.message_container('Warning',
					'Adult Content Blocked: {}'.format(warning_string))

	# page category stings depending on media
	page_category = 'Chapter(s)' if (type_title == 'Manga' or type_title == 'Comic') else 'Video(s)'

	# update item_info to include page_category
	item_info.update({'page_category': page_category})

	# format item_url for parsing
	Logger('* page url = {}'.format(page_url))
	Logger('* base url = {}'.format(base_url))
	Logger('*' * 80)
	if not item_info['cover_url']:
		try:
			cover_url = Common.CorrectCoverImage(html.xpath('//head/link[@rel="image_src"]')[0].get('href'))
			if Common.is_kiss_url(cover_url):
				content_url = Common.GetBaseURL(cover_url) + '/' + cover_url.split('/', 3)[3]
				image_file = content_url.rsplit('/')[-1]
			else:
				content_url = cover_url
				image_file = cover_url.split('/', 3)[3].replace('/', '_')
			item_info.update({'cover_url': content_url, 'cover_file': image_file})
		except:
			pass
	cover = Callback(GetThumb, cover_url=item_info['cover_url'], cover_file=item_info['cover_file'])

	if ('Manga' in type_title) or ('Comic' in type_title):
		manga_info = Metadata.GetBaseMangaInfo(html, page_url)
		summary = manga_info['summary'] if manga_info['summary'] else (item_info['short_summary'] if item_info['short_summary'] else None)
		item_info.update({'summary': summary})
		item_info.pop('short_summary')
		manga_info.pop('summary')
		summary2 = Common.StringCode(string=summary, code='decode')

		oc.add(TVShowObject(
			key=Callback(MangaSubPage, item_info=item_info, manga_info=manga_info),
			rating_key=page_url, title=manga_info['title'], genres=genres,
			source_title=manga_info['source_title'], summary=unicode(summary2),
			thumb=cover, art=R(art)
			))

	elif 'Movie' in genres:
		movie_info = Metadata.GetBaseMovieInfo(html, page_url)
		summary = movie_info['summary'] if movie_info['summary'] else (item_info['short_summary'] if item_info['short_summary'] else None)
		item_info.update({'summary': summary})
		item_info.pop('short_summary')
		movie_info.pop('summary')
		summary2 = Common.StringCode(string=summary, code='decode')

		oc.add(TVShowObject(
			key=Callback(MovieSubPage, item_info=item_info, movie_info=movie_info),
			rating_key=page_url, title=movie_info['title'], genres=genres,
			source_title=movie_info['source_title'], summary=unicode(summary2),
			thumb=cover, art=R(art)
			))

	else:
		show_info = Metadata.GetBaseShowInfo(html, page_url)
		summary = show_info['summary'] if show_info['summary'] else (item_info['short_summary'] if item_info['short_summary'] else None)
		item_info.update({'summary': summary})
		item_info.pop('short_summary')
		show_info.pop('summary')
		summary2 = Common.StringCode(string=summary, code='decode')

		oc.add(TVShowObject(
			key=Callback(ShowSubPage, item_info=item_info, show_info=show_info),
			rating_key=page_url, title=show_info['tv_show_name'], genres=genres,
			source_title=show_info['source_title'], summary=unicode(summary2),
			thumb=cover, art=R(art)
			))

	# Setup related links
	related = []
	if type_title == 'Comic':
		jdata = JSON.ObjectFromURL(
			base_url + '/GetRelatedLinks', method='POST', cacheTime=CACHE_1HOUR,
			values={'keyword': page_url.split('/')[-1].replace('-', '+')},
			headers=Headers.get_headers_for_url(base_url)
			)
		for jd in jdata:
			rel_title = jd['Name']
			rel_url = jd['Link']
			rel_item_info = {
				'item_sys_name': Common.StringCode(string=rel_url.split('/')[-1], code='encode'),
				'item_title': Common.StringCode(string=rel_title, code='encode'),
				'short_summary': 'NA', 'cover_url': "", 'cover_file': "",
				'type_title': type_title, 'base_url': base_url, 'page_url': rel_url, 'art': art
				}
			related.append(rel_item_info)
	else:
		for rel in html.xpath('//a[starts-with(@href, "/{}/")]'.format(type_title)):
			hrel = rel.get('href')
			if (len(hrel.split('/')) == 3) and (hrel != '/'+page_url.split('/', 3)[3]):
				rel_title = rel.text_content().strip()
				rel_item_info = {
					'item_sys_name': Common.StringCode(string=hrel.split('/')[-1], code='encode'),
					'item_title': Common.StringCode(string=rel_title, code='encode'),
					'short_summary': 'NA', 'cover_url': "", 'cover_file': "",
					'type_title': type_title, 'base_url': base_url, 'page_url': base_url + hrel, 'art': art
					}
				related.append(rel_item_info)
	if related:
		oc.add(DirectoryObject(
			key=Callback(RelatedList, r_list=related, title=item_title_decode, art=art),
			title='Related Links', thumb=R('icon-related.png'), art=R(art)))

	# Test if the Dict does have the 'Bookmarks' section
	bm = Dict['Bookmarks']
	if ((True if [b[type_title] for b in bm[type_title] if b[type_title] == item_sys_name] else False) if type_title in bm.keys() else False) if bm else False:
		# provide a way to remove Item from bookmarks list
		oc.add(DirectoryObject(
			key=Callback(RemoveBookmark, item_info=item_info),
			title='Remove Bookmark', thumb=R(BOOKMARK_REMOVE_ICON),
			summary=u'Remove \"{}\" from your Bookmarks list.'.format(item_title_decode)))
	else:
		# Item not in 'Bookmarks' yet, so lets parse it for adding!
		oc.add(DirectoryObject(
			key=Callback(AddBookmark, item_info=item_info),
			title='Add Bookmark', thumb=R(BOOKMARK_ADD_ICON),
			summary=u'Add \"{}\" to your Bookmarks list.'.format(item_title_decode)))

	return oc

####################################################################################################
@route(PREFIX + '/item-related', r_list=list)
def RelatedList(r_list, title, art):
	"""Setup Related shows list"""

	if len(r_list) == 1:
		return ItemPage(r_list[0])

	oc = ObjectContainer(title2=unicode(title) + u' / Related', art=R(art))
	for r_info in r_list:
		oc.add(DirectoryObject(
			key=Callback(ItemPage, item_info=r_info),
			title=unicode(Common.StringCode(string=r_info['item_title'], code='decode')),
			art=R(art)
			))
	return oc

####################################################################################################
def GetItemList(html, url, item_title, type_title):
	"""Get list of Episodes, Movies, or Chapters"""

	episode_list = html.xpath('//table[@class="listing"]/tr/td')
	item_title_decode = Common.StringCode(string=item_title, code='decode')
	item_title_regex = RE_TITLE_CLEAN_DOT.sub('', item_title_decode)

	# if no shows, then none have been added yet
	if not episode_list:
		return 'Not Yet Aired'

	a = []
	b = []
	c = []

	for media in episode_list:
		if media.xpath('./a'):
			node = media.xpath('./a')

			# url for Video/Chapter
			media_page_url = url + '/' + node[0].get('href').rsplit('/')[-1]

			# title for Video/Chapter, cleaned
			raw_title = RE_TITLE_CLEAN_DOT.sub('', node[0].text).replace(item_title_regex, '')
			if ('Manga' in type_title) or ('Comic' in type_title):
				media_title = raw_title.replace('Read Online', '').strip()
			else:
				media_title = raw_title.replace('Watch Online', '').strip()

			a.append((media_page_url, media_title))
		else:
			# date Video/Chapter added
			date = media.text.strip()
			b.append(date)

	for x, y in reversed(map(None, a, b)):
		c.append({'title':x[1], 'date': y, 'url': x[0]})

	return c

####################################################################################################
@route(PREFIX + '/movie-sub-page', item_info=dict, movie_info=dict)
def MovieSubPage(item_info, movie_info):
	"""Setup Movie Page"""

	item_title_decode = Common.StringCode(string=item_info['item_title'], code='decode')
	title2 = u'{} | {} | {}'.format(item_info['type_title'], item_title_decode, item_info['page_category'].lower())

	oc = ObjectContainer(title2=title2, art=R(item_info['art']))

	html = RHTML.ElementFromURL(item_info['page_url'])
	
	base_url = item_info['base_url']
	
	movie_list = GetItemList(html, item_info['page_url'], item_info['item_title'], item_info['type_title'])
	if movie_list == 'Not Yet Aired':
		return MC.message_container(u'Warning', '{} \"{}\" Not Yet Aired.'.format(item_info['type_title'], item_title_decode))

	summary = unicode(Common.StringCode(string=item_info['summary'], code='decode')) if item_info['summary'] else None
	cover = Callback(GetThumb, cover_url=item_info['cover_url'], cover_file=item_info['cover_file'])
	genres, genres_list = Metadata.GetGenres(html)
	
	if Prefs['use_captcha_solver'] == True:
		for movie in movie_list:
			title = '{} | {}'.format(movie['title'], movie['date'])
			oc.add(DirectoryObject(
					title=title,
					key=Callback(VideoItemPage, item_url=movie['url'], title=title, summary=summary, thumb=cover, art=item_info['art'], rapidPage=movie['url'], base_url=base_url),
					summary=summary,
					thumb=cover,
					art=R(item_info['art'])
				))
	else:
		for movie in movie_list:
			oc.add(MovieObject(
				title='{} | {}'.format(movie['title'], movie['date']),
				source_title=movie_info['source_title'],
				summary=summary,
				year=int(movie_info['year']) if movie_info['year'] else None,
				genres=genres if genres else [],
				originally_available_at=Datetime.ParseDate(movie['date']) if movie['date'] else None,
				thumb=cover,
				art=R(item_info['art']),
				url=movie['url']
				))

	return oc

####################################################################################################
@route(PREFIX + '/video-item-page', item_info=dict, movie_info=dict)
def VideoItemPage(item_url, title, summary, thumb, art, refresh=0, rapidPage=None, base_url=None):

	rapidPage = rapidPage if rapidPage != None else item_url
	
	if kissanimesolver.getProgress(item_url) == -1:
		Thread.Create(kissanimesolver.solveKA, {}, item_url, rapidPage, base_url)
		time.sleep(7)
	else:
		if kissanimesolver.getProgress(item_url) != 100:
			time.sleep(10)
	
	prog = kissanimesolver.getProgress(item_url)
	blocked_bool, blocked_msg = kissanimesolver.getBlockStatus()
	
	if blocked_bool == True:
		return MC.message_container('Blocking',blocked_msg)
	elif prog == 100:
		playurls = kissanimesolver.getPlayUrls(item_url)
		oc = ObjectContainer(title2 = unicode(title))
		
		for server in playurls.keys():
			vvv = playurls[server]['video']
			if vvv != None:
				for vv in vvv:
					vidurl = vv['link']
					if vidurl != None:
						qual = vv['qual']
						titlex = '%s (%s - %s)' % (title, server, qual)
						try:
							oc.add(CreateVideoObject(vidurl, titlex, summary, thumb))
						except Exception as e:
							Log("ERROR : VideoItemPage > %s" % e)
		return oc
	else:
		#return MC.message_container(u'Please wait and try again: %s' % (str(prog)+'%'), u'Progress: %s. Please wait (Solver working) and try again. It can take from few sec.s to few min.s' % (str(prog)+'%'))
		oc = ObjectContainer(title2 = unicode('Refresh - %s' % (str(prog)+'%'),))
		oc.add(DirectoryObject(
			title='Refresh (%s) - %s' % ((str(prog)+'%'), title),
			key=Callback(VideoItemPage, item_url=item_url, title=title, summary=summary, thumb=thumb, art=art, refresh=int(refresh)+1),
			summary='Progress: %s. Please wait (Solver working) and try again. It can take from few sec.s to few min.s' % (str(prog)+'%'),
			thumb=thumb,
			art=art
		))
		return oc

####################################################################################################
@route(PREFIX + '/manga-sub-page', item_info=dict, manga_info=dict)
def MangaSubPage(item_info, manga_info):
	"""Create the Manga/Comic Sub Page with Chapter list"""
	#TODO split this into ~30 chapters per book or so, similar to what was done with seasons

	item_title_decode = Common.StringCode(string=item_info['item_title'], code='decode')
	title2 = u'{} | {} | {}'.format(item_info['type_title'], item_title_decode, item_info['page_category'].lower())

	oc = ObjectContainer(title2=title2, art=R(item_info['art']))
	html = RHTML.ElementFromURL(item_info['page_url'])

	cp_list = GetItemList(html, item_info['page_url'], item_info['item_title'], item_info['type_title'])
	if cp_list == 'Not Yet Aired':
		return MC.message_container(u'Warning', '{} \"{}\" Not Yet Aired.'.format(item_info['type_title'], item_title_decode))

	cover = Callback(GetThumb, cover_url=item_info['cover_url'], cover_file=item_info['cover_file'])
	for cp in reversed(cp_list):
		oc.add(PhotoAlbumObject(
			key=Callback(GetPhotoAlbum,
				url=cp['url'], source_title=manga_info['source_title'], title=cp['title'],
				art=item_info['art']),
			rating_key=cp['url'],
			title='{} | {}'.format(cp['title'], cp['date']),
			source_title=manga_info['source_title'],
			originally_available_at=Datetime.ParseDate(cp['date']) if cp['date'] else None,
			thumb=cover,
			art=R(item_info['art'])
			))

	return oc

####################################################################################################
@route(PREFIX + '/getphotoablum')
def GetPhotoAlbum(url, source_title, title, art):
	"""
	This function pulls down all the image urls for a chapter and adds them to the
	'PhotoObject' container.
	"""

	oc = ObjectContainer(title2=title, art=R(art))

	page = HTML.StringFromElement(RHTML.ElementFromURL(url))
	images = Regex(r'lstImages\.push\(["\'](http[^"\']+)["\']').findall(page)
	for image in images:
		name = image.rsplit('/')[-1].rsplit('.', 1)[0]
		if "proxy" in name:
			name = name.rsplit('%')[-1].rsplit('2f')[1]

		oc.add(CreatePhotoObject(
			url=image, source_title=source_title, art=art, title=name
			))

	return oc

####################################################################################################
@route(PREFIX + '/show-sub-page', item_info=dict, show_info=dict)
def ShowSubPage(item_info, show_info):
	"""Setup Show page"""

	item_title_decode = Common.StringCode(string=item_info['item_title'], code='decode')
	title2 = u'{} | {} | {}'.format(item_info['type_title'], item_title_decode, item_info['page_category'].lower())

	oc = ObjectContainer(title2=title2, art=R(item_info['art']))

	html = RHTML.ElementFromURL(item_info['page_url'])
	ep_list = GetItemList(html, item_info['page_url'], item_info['item_title'], item_info['type_title'])
	if ep_list == 'Not Yet Aired':
		return MC.message_container(u'Warning', '{} \"{}\" Not Yet Aired.'.format(item_info['type_title'], item_title_decode))
	else:
		tags = Metadata.string_to_list(Common.StringCode(string=show_info['tags'], code='decode')) if show_info['tags'] else []
		thumb = Callback(GetThumb, cover_url=item_info['cover_url'], cover_file=item_info['cover_file'])
		summary = unicode(Metadata.GetSummary(html))
		show_name_raw = html.xpath('//div[@class="barContent"]/div/a[@class="bigChar"]/text()')[0]
		season_dict = None
		main_ep_count = len(ep_list)
		ips = 30
		cp = Client.Product
		season_info = {
			'season': '1', 'ep_count': main_ep_count, 'tv_show_name': show_info['tv_show_name'],
			'art': item_info['art'], 'source_title': show_info['source_title'],
			'page_url': item_info['page_url'], 'cover_url': item_info['cover_url'],
			'cover_file': item_info['cover_file'], 'year': show_info['year'], 'tags': show_info['tags'],
			'item_title': item_info['item_title'], 'type_title': item_info['type_title'], 'ips': str(ips)
			}

		Logger('*' * 80)
		Logger('* ep_list lenght = {}'.format(main_ep_count))

		for ep in ep_list:
			title_lower = ep['title'].lower()

			if 'episode' in title_lower and 'uncensored' not in title_lower:
				season_number = Metadata.GetSeasonNumber(ep['title'], show_name_raw, tags, summary)
			else:
				season_number = '0'

			if not season_dict:
				season_dict = {season_number: [ep['title']]}
			elif season_number in season_dict.keys():
				season_dict[season_number].append(ep['title'])
			else:
				season_dict.update({season_number: [ep['title']]})

		for season in sorted(season_dict.keys()):
			ep_count = len(season_dict[season])
			Logger('* ep_count = {}'.format(ep_count))
			s0 = (ep_count if season == '0' else (len(season_dict['0']) if '0' in season_dict.keys() else 0))
			season_info.update({'season': season, 'ep_count': ep_count, 'fseason': season, 'season0': s0})
			ep_info = '' if cp in CP_DATE else ' | {} Episodes'.format(ep_count)
			s0_summary = '{}: S0 Specials, Uncensored Episodes, and Miscellaneous Videos{}'.format(show_info['tv_show_name'], ep_info)
			s_summary = '{}: S{} Episodes{}'.format(show_info['tv_show_name'], season, ep_info)
			if (ep_count > ips) and (season != '0'):
				season = int(season)
				x, r = divmod(main_ep_count-s0, ips)
				nseason_list = [str(t) for t in xrange(season, x + (1 if r > 0 else 0) + season)]
				Logger('* new season list = {}'.format(nseason_list))
				for i, nseason in enumerate(nseason_list):
					nep_count = ((ips if r == 0 else r) if i+1 == len(nseason_list) else ips)
					Logger('* nep_count = {}'.format(nep_count))
					season_info.update({'season': nseason, 'ep_count': nep_count, 'fseason': str(i+1)})
					nep_info = '' if cp in CP_DATE else ' | {} Episodes'.format(nep_count)
					s_summary = '{}: S{} seperated out S{} into multiple seasons{}'.format(show_info['tv_show_name'], nseason, season, nep_info)
					oc.add(SeasonObject(
						key=Callback(SeasonSubPage, season_info=season_info),
						rating_key=item_info['page_url'] + nseason,
						title='Season {}'.format(nseason), show=show_info['tv_show_name'],
						index=int(nseason), episode_count=nep_count,
						source_title=show_info['source_title'], thumb=thumb, art=R(item_info['art']),
						summary=s_summary
						))
			else:
				oc.add(SeasonObject(
					key=Callback(SeasonSubPage, season_info=season_info),
					rating_key=item_info['page_url'] + season,
					title='Season {}'.format(season), show=show_info['tv_show_name'],
					index=int(season), episode_count=ep_count,
					source_title=show_info['source_title'], thumb=thumb, art=R(item_info['art']),
					summary=s0_summary if season == '0' else s_summary
					))

		Logger('*' * 80)
		return oc

####################################################################################################
@route(PREFIX + '/season-sub-page', season_info=dict)
def SeasonSubPage(season_info):
	"""Setup Episodes for Season"""

	title2 = u'{} | Season {}'.format(season_info['tv_show_name'], season_info['season'])

	oc = ObjectContainer(title2=title2, art=R(season_info['art']))

	html = RHTML.ElementFromURL(season_info['page_url'])

	ep_list = GetItemList(html, season_info['page_url'], season_info['item_title'], season_info['type_title'])
	tags = Metadata.string_to_list(Common.StringCode(string=season_info['tags'], code='decode')) if season_info['tags'] else []
	thumb = Callback(GetThumb, cover_url=season_info['cover_url'], cover_file=season_info['cover_file'])
	summary = unicode(Metadata.GetSummary(html))
	show_name_raw = html.xpath('//div[@class="barContent"]/div/a[@class="bigChar"]/text()')[0]
	ips = int(season_info['ips'])
	cp = Client.Product

	ep_list2 = []
	for ep in ep_list:
		ep_name, ep_number = Metadata.GetEpisodeNameAndNumber(html, ep['title'], ep['url'])
		season_number = Metadata.GetSeasonNumber(ep['title'], show_name_raw, tags, summary)
		if season_number == season_info['season']:
			ep.update({'season_number': season_number, 'ep_number': ep_number})
			ep_list2.append(ep)

	if ((len(ep_list2) > ips and season_info['season'] != '0') or (len(ep_list2) == 0)):
		temp = int(season_info['fseason'])
		s0 = int(season_info['season0'])
		if len(ep_list2) == 0:
			nep_list = ep_list[ ( ((temp-1)*ips) + s0 ) : ((temp*ips) + s0) ]
		else:
			nep_list = ep_list2[((temp - 1)*ips):((temp)*ips)]
		for nep in nep_list:
			ep_name, ep_number = Metadata.GetEpisodeNameAndNumber(html, nep['title'], nep['url'])
			season_number = Metadata.GetSeasonNumber(nep['title'], show_name_raw, tags, summary)
			if Prefs['use_captcha_solver'] == True:
				title = nep['title'] if cp in CP_DATE else '{} | {}'.format(nep['title'], (nep['date'] if nep['date'] else 'NA'))
				oc.add(DirectoryObject(
						title=title,
						key=Callback(VideoItemPage, item_url=nep['url'], title=title, summary=title, thumb=thumb, art=season_info['art']),
						summary=title,
						thumb=thumb,
						art=R(season_info['art'])
					))
			else:
				oc.add(EpisodeObject(
					source_title=season_info['source_title'],
					title=nep['title'] if cp in CP_DATE else '{} | {}'.format(nep['title'], (nep['date'] if nep['date'] else 'NA')),
					show=season_info['tv_show_name'],
					season=int(season_number),
					index=int(ep_number),
					thumb=thumb,
					art=R(season_info['art']),
					originally_available_at=Datetime.ParseDate(nep['date']) if nep['date'] else None,
					url=nep['url']
				))
	else:
		for ep in ep_list2:
			if Prefs['use_captcha_solver'] == True:
				title=ep['title'] if cp in CP_DATE else '{} | {}'.format(ep['title'], (ep['date'] if ep['date'] else 'NA'))
				oc.add(DirectoryObject(
					title=title,
					key=Callback(VideoItemPage, item_url=ep['url'], title=title, summary=title, thumb=thumb, art=season_info['art']),
					summary=title,
					thumb=thumb,
					art=R(season_info['art'])
				))
			else:
				oc.add(EpisodeObject(
					source_title=season_info['source_title'],
					title=ep['title'] if cp in CP_DATE else '{} | {}'.format(ep['title'], (ep['date'] if ep['date'] else 'NA')),
					show=season_info['tv_show_name'],
					season=int(ep['season_number']),
					index=int(ep['ep_number']),
					thumb=thumb,
					art=R(season_info['art']),
					originally_available_at=Datetime.ParseDate(ep['date']) if ep['date'] else None,
					url=ep['url']
				))

	return oc

####################################################################################################
@route(PREFIX + '/create-photo-object', include_container=bool)
def CreatePhotoObject(title, url, art, source_title, include_container=False, *args, **kwargs):

	photo_object = PhotoObject(
		key=Callback(CreatePhotoObject,
			title=title, url=url, art=art, source_title=source_title, include_container=True),
		rating_key=url,
		source_title=source_title,
		title=title,
		thumb=url,
		art=R(art),
		items=[MediaObject(parts=[PartObject(key=url)])]
		)

	if include_container:
		return ObjectContainer(objects=[photo_object])
	return photo_object

####################################################################################################
@route(PREFIX + '/search')
def Search(query=''):
	"""Set up Search for kiss(anime, asian, cartoon, manga)"""

	# set defaults
	query = query.strip()
	title2 = u'Search for \"{}\" in...'.format(query)

	oc = ObjectContainer(title2=title2)

	# format each search url and send to 'SearchPage'
	# can't check each url here, would take too long since behind cloudflare and timeout the server
	prefs_names = ['kissanime', 'kissasian', 'kisscartoon', 'kissmanga', 'kisscomic']
	b_prefs_names = [p for p in prefs_names if Prefs[p]]
	if len(b_prefs_names) == 1:
		b_prefs_name = b_prefs_names[0]
		b_prefs_name = 'comic' if b_prefs_name == 'kisscomic' else b_prefs_name
		search_url = [s for s in Common.SearchURLList() if b_prefs_name in s][0]
		search_url_filled = search_url.format(String.Quote(query, usePlus=True))
		type_title = 'Drama' if b_prefs_name == 'kissasian' else (b_prefs_name.split('kiss')[1].title() if 'kiss' in b_prefs_name else 'Comic')
		art = 'art-{}.jpg'.format(type_title.lower())

		html = RHTML.ElementFromURL(search_url_filled)
		if html.xpath('//table[@class="listing"]'):
			return SearchPage(type_title=type_title, search_url=search_url_filled, art=art)
	else:
		Logger('*' * 80)
		for search_url in Common.SearchURLList():
			search_url_filled = search_url.format(String.Quote(query, usePlus=True))
			type_title = Common.GetTypeTitle(search_url_filled)
			# change kissasian info to 'Drama'
			art = 'art-{}.jpg'.format(type_title.lower())
			thumb = 'icon-{}.png'.format(type_title.lower())
			prefs_name = 'kissasian' if type_title == 'Drama' else 'kiss{}'.format(type_title.lower())

			if Prefs[prefs_name]:
				Logger('* Search url = {}'.format(search_url_filled))
				Logger('* type title = {}'.format(type_title))

				listing = True
				if Prefs['search_all']:
					html = RHTML.ElementFromURL(search_url_filled)
					listing = bool(html.xpath('//table[@class="listing"]'))

				if listing:
					oc.add(DirectoryObject(
						key=Callback(SearchPage, type_title=type_title, search_url=search_url_filled, art=art),
						title=type_title, thumb=R(thumb)
						))

	if len(oc) > 0:
		Logger('*' * 80)
		return oc
	else:
		Logger('* Search retunred no results')
		Logger('*' * 80)
	return MC.message_container('Search',
		'There are no search results for \"{}\". Try being less specific or make sure at least one source is selected in Preferences.'.format(query))

####################################################################################################
@route(PREFIX + '/searchpage')
def SearchPage(type_title, search_url, art):
	"""
	Retrun searches for each kiss() page
	The results can return the Item itself via a url redirect.
	Check for "exact" matches and send them to ItemPage
	If normal seach result then send to DirectoryList
	"""

	html = RHTML.ElementFromURL(search_url)
	cover_url = None
	cover_file = None

	# Check for results if none then give a pop up window saying so
	if html.xpath('//table[@class="listing"]'):
		# Test for "exact" match, if True then send to 'ItemPage'
		node = html.xpath('//div[@id="headnav"]/script/text()')[0]
		search_match = Regex(r"var\ path\ =\ ('Search')").search(node)
		if not search_match:
			# Send url to 'ItemPage'
			base_url = Common.GetBaseURL(search_url)
			node = html.xpath('//div[@class="barContent"]/div/a')[0]

			item_sys_name = Common.StringCode(string=node.get('href').rsplit('/')[-1].strip(), code='encode')
			item_url = base_url + '/' + type_title + '/' + Common.StringCode(item_sys_name, code='encode')
			item_title = node.text
			try:
				cover_url = Common.CorrectCoverImage(html.xpath('//head/link[@rel="image_src"]')[0].get('href'))
				if ('http' in cover_url) and Common.is_kiss_url(cover_url):
					cover_file = cover_url.rsplit('/')[-1]
				elif 'http' in cover_url:
					cover_file = cover_url.split('/', 3)[3].replace('/', '_')
			except:
				Log.Warn("* Cannot find cover URL/File for '{}'".format(search_url))

			Logger('* item_title	= {}'.format(item_title))
			Logger('* item		  = {}'.format(item_sys_name))
			Logger('* type_title	= {}'.format(type_title))
			Logger('* base_url	  = {}'.format(base_url))
			Logger('* item_url	  = {}'.format(item_url))

			item_info = {
				'item_sys_name': item_sys_name,
				'item_title': Common.StringCode(string=item_title, code='encode'),
				'short_summary': None,
				'cover_url': cover_url,
				'cover_file': cover_file,
				'type_title': type_title,
				'base_url': base_url,
				'page_url': item_url,
				'art': art}

			return ItemPage(item_info=item_info)
		else:
			# Send results to 'DirectoryList'
			query = search_url.rsplit('=')[-1]
			Logger('* art		   = {}'.format(art))
			Logger('*' * 80)
			return DirectoryList(1, 'Search', query, search_url, type_title, art)
	# No results found :( keep trying
	else:
		Logger('* Search returned no results.', kind='Warn')
		Logger('*' * 80)
		query = search_url.rsplit('=')[-1]
		return MC.message_container('Search',
			u"""
			There are no search results for \"{}\" in \"{}\" Category.
			Try being less specific.
			""".format(query, type_title))

####################################################################################################
@route(PREFIX + '/addbookmark', item_info=dict)
def AddBookmark(item_info):
	"""Adds Item to the bookmarks list"""

	# set variables
	item_sys_name = item_info['item_sys_name']
	item_title = item_info['item_title']
	type_title = item_info['type_title']
	cover_url = item_info['cover_url']
	page_url = item_info['page_url']

	# decode title string
	item_title_decode = Common.StringCode(string=item_title, code='decode')
	Logger('*' * 80)
	Logger(u'* item to add = {} | {}'.format(item_title_decode, item_sys_name), kind='Info')

	# setup html for parsing
	html = RHTML.ElementFromURL(page_url)

	# Genres
	genres = html.xpath('//p[span[@class="info"]="Genres:"]/a/text()')
	if genres:
		genres = ' '.join([g.replace(' ', '_') for g in genres])
	else:
		genres = ''

	# if no cover url then try and find one on the item page
	if cover_url:
		cover_url = Common.CorrectCoverImage(cover_url)
		image_file = item_info['cover_file']
	else:
		try:
			cover_url = Common.CorrectCoverImage(html.xpath('//head/link[@rel="image_src"]')[0].get('href'))
			if not 'http' in cover_url:
				cover_url = None
				image_file = None
			else:
				image_file = cover_url.split('/', 3)[3].replace('/', '_')
		except:
			cover_url = None
			image_file = None

	# get summary
	summary = Metadata.GetSummary(html)

	# setup new bookmark json data to add to Dict
	new_bookmark = {
		type_title: item_sys_name, 'item_title': item_title, 'cover_file': image_file,
		'cover_url': cover_url, 'summary': summary, 'genres': genres, 'page_url': page_url,
		'date_added': str(Datetime.UTCNow())
		}

	Logger('* new bookmark to add >>')
	Logger(u'* {}'.format(new_bookmark))

	bm = Dict['Bookmarks']

	# Test if the Dict has the 'Bookmarks' section yet
	if not bm:
		# Create new 'Bookmarks' section and fill with the first bookmark
		Dict['Bookmarks'] = {type_title: [new_bookmark]}
		Logger('* Inital bookmark list created >>')
		Logger(u'* {}'.format(bm))
		Logger('*' * 80)

		# Update Dict to include new 'Bookmarks' section
		Dict.Save()

		# Provide feedback that the Item has been added to bookmarks
		return MC.message_container(unicode(item_title_decode),
			u'\"{}\" has been added to your bookmarks.'.format(item_title_decode))
	# check if the category key 'Anime', 'Manga', 'Cartoon', 'Drama', or 'Comic' exist
	# if so then append new bookmark to one of those categories
	elif type_title in bm.keys():
		# fail safe for when clients are out of sync and it trys to add the bookmark in duplicate
		if (True if [b[type_title] for b in bm[type_title] if b[type_title] == item_sys_name] else False):
			# Bookmark already exist, don't add in duplicate
			Logger(u'* bookmark \"{}\" already in your bookmarks'.format(item_title_decode), kind='Info')
			Logger('*' * 80)
			return MC.message_container(unicode(item_title_decode),
				u'\"{}\" is already in your bookmarks.'.format(item_title_decode))
		# append new bookmark to its correct category, i.e. 'Anime', 'Drama', etc...
		else:
			temp = {}
			temp.setdefault(type_title, bm[type_title]).append(new_bookmark)
			Dict['Bookmarks'][type_title] = temp[type_title]
			Logger(u'* bookmark \"{}\" has been appended to your {} bookmarks'.format(item_title_decode, type_title), kind='Info')
			Logger('*' * 80)

			# Update Dict to include new Item
			Dict.Save()

			# Provide feedback that the Item has been added to bookmarks
			return MC.message_container(unicode(item_title_decode),
				u'\"{}\" has been added to your bookmarks.'.format(item_title_decode))
	# the category key does not exist yet so create it and fill with new bookmark
	else:
		Dict['Bookmarks'].update({type_title: [new_bookmark]})
		Logger(u'* bookmark \"{}\" has been created in new {} section in bookmarks'.format(item_title_decode, type_title), kind='Info')
		Logger('*' * 80)

		# Update Dict to include new Item
		Dict.Save()

		# Provide feedback that the Item has been added to bookmarks
		return MC.message_container(unicode(item_title_decode),
			u'\"{}\" has been added to your bookmarks.'.format(item_title_decode))

####################################################################################################
@route(PREFIX + '/removebookmark', item_info=dict)
def RemoveBookmark(item_info):
	"""Removes item from the bookmarks list using the item as a key"""

	# set variables
	item_sys_name = item_info['item_sys_name']
	item_title = item_info['item_title']
	type_title = item_info['type_title']

	# decode string
	item_title_decode = unicode(Common.StringCode(string=item_title, code='decode'))

	# index 'Bookmarks' list
	bm = Dict['Bookmarks'][type_title]
	Logger('* bookmark length = {}'.format(len(bm)))
	for i in xrange(len(bm)):
		# remove item's data from 'Bookmarks' list
		if bm[i][type_title] == item_sys_name:
			# if caching covers, then don't remove cover file
			bm.pop(i)
			break

	# update Dict, and debug log
	Dict.Save()
	Logger('* \"{}\" has been removed from Bookmark List'.format(item_title_decode), kind='Info')

	if len(bm) == 0:
		# if the last bookmark was removed then clear it's bookmark section
		Logger('* {} bookmark was the last, so removed {} bookmark section'.format(item_title_decode, type_title), force=True)
		Logger('*' * 80)
		return ClearBookmarksCheck(type_title)
	else:
		Logger('*' * 80)
		# Provide feedback that the Item has been removed from the 'Bookmarks' list
		return MC.message_container(type_title,
			'\"{}\" has been removed from your bookmarks.'.format(item_title_decode))

####################################################################################################
@route(PREFIX + '/clearbookmarks')
def ClearBookmarks(type_title):

	art = 'art-{}.jpg'.format(type_title.lower if type_title != 'All' else 'main')
	oc = ObjectContainer(
		title2=u'Clear \'{}\'?'.format(type_title), art=R(art), no_cache=True
		)
	oc.add(PopupDirectoryObject(
		key=Callback(ClearBookmarksCheck, tt=type_title),
		title='OK?',
		summary='Sure you want to Delete all \'{}\' bookmarks? If NOT then navigate back or away from this page.'.format(type_title),
		thumb=R(BOOKMARK_CLEAR_ICON), art=R(art)
		))
	return oc

####################################################################################################
@route(PREFIX + '/clearbookmarks-yes')
def ClearBookmarksCheck(tt):
	"""Remove 'Bookmarks' Section(s) from Dict. Note: This removes all bookmarks in list"""

	Logger('*' * 80)
	if 'All' in tt:
		# delete 'Bookmarks' section from Dict
		if Dict['Bookmarks']:
			del Dict['Bookmarks']
			Logger('* Entire Bookmark Dict Removed')
		else:
			Logger('* Entire Bookmark Dict already removed.')
	else:
		# delete section 'Anime', 'Manga', 'Cartoon', 'Drama', or 'Comic' from bookmark list
		if Dict['Bookmarks'] and tt in Dict['Bookmarks'].keys():
			del Dict['Bookmarks'][tt]
			Logger('* \"{}\" Bookmark Section Cleared'.format(tt))
		else:
			Logger('* \"{}\" Bookmark Section Already Cleared'.format(tt))

	Dict['Bookmark_Deleted'] = {'bool': True, 'type_title': tt}
	status = Dict['Bookmark_Deleted']
	Logger('*' * 80)

	Dict.Save()

	# Provide feedback that the correct 'Bookmarks' section is removed
	#   and send back to Bookmark Main Menu
	return BookmarksMain(title='My Bookmarks', status=status)

####################################################################################################
def UpdateLegacyBookmark(bm_info=dict, new_cover=False):
	"""
	Update Old Bookmark to new Style of bookmarks.
	Update includes "Genres" for now, will add more here later if need be
	"""

	type_title = bm_info['type_title']
	item_title = bm_info['item_title']
	item_title_decode = Common.StringCode(string=item_title, code='decode')
	base_url = bm_info['base_url']
	page_url = base_url + '/' + bm_info['page_url'].split('/', 3)[3]

	html = RHTML.ElementFromURL(page_url)

	cover_url = None
	if bm_info['cover_url'] and (Common.is_kiss_url(bm_info['cover_url']) == False):
		cover_url = bm_info['cover_url']
	elif bm_info['cover_url'] and (base_url in bm_info['cover_url']):
		cover_url = base_url + '/' + bm_info['cover_url'].split('/', 3)[3]

	if new_cover or (not cover_url):
		try:
			cover_url = Common.CorrectCoverImage(html.xpath('//head/link[@rel="image_src"]')[0].get('href'))
			if not 'http' in cover_url:
				cover_url = None
		except:
			cover_url = None

	if 'genres' not in bm_info.keys():
		genres = html.xpath('//p[span[@class="info"]="Genres:"]/a/text()')
		if genres:
			genres = ' '.join([g.replace(' ', '_') for g in genres])
		else:
			genres = ''
	else:
		genres = bm_info['genres']

	new_bookmark = {
		type_title: bm_info['item_sys_name'], 'item_title': item_title,
		'cover_file': bm_info['cover_file'], 'cover_url': cover_url,
		'summary': bm_info['short_summary'], 'genres': genres, 'page_url': page_url,
		'date_added': bm_info['date_added'] if 'date_added' in bm_info.keys() else str(Datetime.UTCNow()),
		}

	bm = Dict['Bookmarks'][type_title]
	for i in xrange(len(bm)):
		if bm[i][type_title] == new_bookmark[type_title]:
			Log.Debug('*' * 80)

			bm[i].update(new_bookmark)
			Log.Debug(u'* {} Bookmark \"{}\" Updated'.format(type_title, item_title_decode))
			Log.Debug(u'* updated bookmark = {}'.format(bm[i]))
			Log.Debug('*' * 80)
			break

	# Update Dict to include new Item
	Dict.Save()

	return

####################################################################################################
@route(PREFIX + '/dirsize')
def GetDirSize(start_path='.'):
	"""Get Directory Size in Megabytes or Gigabytes. Returns String rounded to 3 decimal places"""

	try:
		bsize = 1000  #1000 decimal, 1024 binary
		total_size = 0
		count = 0
		for dirpath, dirnames, filenames in Core.storage.walk(start_path):
			for f in filenames:
				fp = Core.storage.join_path(dirpath, f)
				if not Core.storage.dir_exists(fp):
					total_size += Core.storage.file_size(fp)
					count += 1

		if total_size > float(1000000000):
			# gigabytes
			for i in range(3):
				total_size = total_size / bsize
			d = '{} Cached | {} GB Used'.format(count, str(round(total_size, 3)))
		elif total_size > float(1000000):
			# megabytes
			for i in range(2):
				total_size = total_size / bsize
			d = '{} Cached | {} MB Used'.format(count, str(round(total_size, 3)))
		else:
			# kilobytes
			for i in range(1):
				total_size = total_size / bsize
			d = '{} Cached | {} kB Used'.format(count, str(round(total_size, 3)))

		return d
	except:
		return 'Error'
		
####################################################################################################
@route(PREFIX+'/videoplayback')
def CreateVideoObject(url, title, summary, thumb, include_container=False, **kwargs):

	if include_container:
		video = MovieObject(
			key = Callback(CreateVideoObject, url=url, title=title, summary=summary, thumb=thumb, include_container=True),
			rating_key = url + title,
			title = title,
			summary = summary,
			thumb = thumb,
			items = [
				MediaObject(
						container = Container.MP4,	 # MP4, MKV, MOV, AVI
						video_codec = VideoCodec.H264, # H264
						audio_codec = AudioCodec.AAC,  # ACC, MP3
						audio_channels = 2,			# 2, 6
						parts = [PartObject(key=Callback(PlayVideo, videoUrl=url))],
						optimized_for_streaming = True
				)
			]
		)
	else:
		video = VideoClipObject(
			key = Callback(CreateVideoObject, url=url, title=title, summary=summary, thumb=thumb, include_container=True),
			rating_key = url + title,
			title = title,
			summary = summary,
			thumb = thumb,
			items = [
				MediaObject(
						container = Container.MP4,	 # MP4, MKV, MOV, AVI
						video_codec = VideoCodec.H264, # H264
						audio_codec = AudioCodec.AAC,  # ACC, MP3
						audio_channels = 2,			# 2, 6
						parts = [PartObject(key=Callback(PlayVideo,videoUrl=url))],
						optimized_for_streaming = True
				)
			]
		)
  
	if include_container:
		return ObjectContainer(objects=[video])
	else:
		return video
		
####################################################################################################
@route(PREFIX+'/PlayVideo.mp4')
@indirect
def PlayVideo(videoUrl, **kwargs):

	return IndirectResponse(VideoClipObject, key=videoUrl)

####################################################################################################
@route(PREFIX + '/get_thumb')
def GetThumb(cover_url, cover_file):
	"""
	Get Thumb
	Return DataObject of cached thumb, or Redirect(cover_url) for non-kiss hosted thumbs
	"""

	cover = None
	if not cover_url:
		Log.Error('* No cover_url')
		return cover
	elif Common.is_kiss_url(cover_url):
		if cover_file:
			type_title = Common.GetTypeTitle(cover_url)
			Logger('* cover file name   = {}'.format(cover_file))
			if KData.CoverExists(Core.storage.join_path(type_title, cover_file)):
				Log.Debug(u'* Loading cover from {} folder'.format(THUMB_CACHE_DIR))
				cover = KData.data_object(KData.Covers(Core.storage.join_path(type_title, cover_file)))
			else:
				Logger('* Cover not yet saved, saving {} now'.format(cover_file))
				try:
					tt, f = SaveCoverImage(cover_url)
					cover = KData.data_object(KData.Covers(Core.storage.join_path(tt, f)))
				except:
					Log.Exception(u'* Cannot Save/Load "{}"'.format(cover_url))
					cover = None
	elif 'http' in cover_url:
		Logger('* Thumb NOT hosted on Kiss, Redirecting URL {}'.format(cover_url))
		cover = Redirect(Common.CorrectCoverImage(cover_url))

	if not cover:
		Log.Error('* There is no cover')
		return None
	return cover

####################################################################################################
@route(PREFIX + '/logger', force=bool)
def Logger(message, force=False, kind=None):
	"""Setup logging options based on prefs, indirect because it has no return"""

	if force or Prefs['debug']:
		if kind == 'Debug' or kind == None:
			Log.Debug(message)
		elif kind == 'Info':
			Log.Info(message)
		elif kind == 'Warn':
			Log.Warn(message)
		elif kind == 'Error':
			Log.Error(message)
		elif kind == 'Critical':
			Log.Critical(message)
	else:
		pass

	return
