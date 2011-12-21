import csv, feedparser, time
from datetime import date
from storefront.models import BlogPostInfo

blog_posts = BlogPostInfo.objects.all()
feed = feedparser.parse( 'http://blog.indextank.com/feed/' )
  
for item in feed['items']:
  if not any(item['link'] == post.url for post in blog_posts ):
    # if there isn't a post with this url, then create it    
    d = date(item['date_parsed'][0], item['date_parsed'][1], item['date_parsed'][2])
    BlogPostInfo.objects.create(url=item['link'].encode('utf-8'), title=item['title'].encode('utf-8'), author=item['author'].encode('utf-8'), date=d)

