#!/usr/bin/env python3
"""Generate verified GitHub stats using GitHub GraphQL; no third-party service."""
import os, urllib.request, json, datetime, collections, pathlib
from xml.sax.saxutils import escape
USER='AhmedKhaledHussein'
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'
TOKEN=os.environ.get('GITHUB_TOKEN','')
if not TOKEN: raise SystemExit('Missing GITHUB_TOKEN; run via GitHub Actions.')
QUERY="""query ($login:String!) {
 user(login:$login) {
  contributionsCollection {
   contributionCalendar {totalContributions weeks {contributionDays {date contributionCount}}}
   totalCommitContributions totalPullRequestContributions totalIssueContributions
  }
  repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER) {
   nodes {isFork languages(first:10,orderBy:{field:SIZE,direction:DESC}) {
     edges {size node {name color}}}}
  }
 }
}
"""
payload=json.dumps({'query':QUERY,'variables':{'login':USER}}).encode()
req=urllib.request.Request('https://api.github.com/graphql',data=payload,
 headers={'Authorization':f'Bearer {TOKEN}','Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'AhmedKhaledHussein-profile-stats'})
with urllib.request.urlopen(req,timeout=25) as f: result=json.load(f)
if result.get('errors'):raise RuntimeError(str(result['errors']))
user=(result.get('data') or {}).get('user')
if not user:raise RuntimeError('User not returned by GitHub GraphQL')
cc=user['contributionsCollection'];cal=cc['contributionCalendar']
all_days=sorted(((datetime.date.fromisoformat(d['date']),d['contributionCount'])
 for w in cal['weeks'] for d in w['contributionDays']),key=lambda x:x[0])
count_by_day=dict(all_days)
today=datetime.datetime.now(datetime.timezone.utc).date()
start=today if count_by_day.get(today,0)>0 else today-datetime.timedelta(days=1)
run=0;t=start
while count_by_day.get(t,0)>0:
 run+=1;t-=datetime.timedelta(days=1)
longest=0;n=0
for _,v in all_days:
 if v>0:n+=1;longest=max(n,longest)
 else:n=0

def esc(s):return escape(str(s),{'"':'&quot;'})
BG='#0D1014';PANEL='#161A20';GOLD='#C7A56A';WHITE='#F4F0E8';MUTED='#ABB0B8'
def start_svg(title,h=310):
 return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{h}" viewBox="0 0 1100 {h}">',
 f'<rect width="1100" height="{h}" fill="{BG}"/>',f'<rect x="2" y="2" width="1096" height="{h-4}" rx="18" fill="{PANEL}" stroke="#41403D" stroke-width="2"/>',
 f'<text x="42" y="62" fill="{WHITE}" font-family="Arial,Helvetica,sans-serif" font-size="29" font-weight="bold">{esc(title)}</text>',
 f'<line x1="40" y1="86" x2="1060" y2="86" stroke="#4C4941" stroke-width="2"/>']
def line(t,x,y,size=24,fill=WHITE,weight=400,anchor='middle'):
 return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" font-family="Arial,Helvetica,sans-serif">{esc(t)}</text>'
updated=datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y UTC')
fields=[('CONTRIBUTIONS',cal['totalContributions']),('COMMITS',cc['totalCommitContributions']),('PULL REQUESTS',cc['totalPullRequestContributions']),('ISSUES',cc['totalIssueContributions'])]
svg=start_svg('GITHUB ACTIVITY  ·  LAST 12 MONTHS',320)
for i,(label,val) in enumerate(fields):
 x=151+i*267
 svg.extend([line(f'{val:,}',x,184,60,GOLD,700),line(label,x,227,19,MUTED,700)])
 if i<3:svg.append(f'<line x1="{x+132}" y1="120" x2="{x+132}" y2="240" stroke="#3A3835"/>')
svg.append(line(f'Current streak: {run} days    ·    Longest streak (12m): {longest} days',550,272,21,WHITE,400))
svg.append(line(f'Updated {updated}',1037,303,14,MUTED,400,anchor='end'))
svg.append('</svg>')
(OUT/'stats-overview.svg').write_text(''.join(svg),encoding='utf8')

language_counts=collections.Counter();colors={}
for repo in user['repositories']['nodes']:
 if repo['isFork']:continue
 for edge in repo['languages']['edges']:
  n=edge['node']['name'];language_counts[n]+=edge['size'];colors[n]=edge['node'].get('color') or GOLD
svg=start_svg('MOST USED LANGUAGES  ·  PUBLIC OWNED REPOS',330)
total=sum(language_counts.values())
if total:
 sorted_lang=language_counts.most_common(5)
 x=48; bar_w=1004
 for name,byt in sorted_lang:
  w=bar_w*byt/total
  svg.append(f'<rect x="{x:.2f}" y="123" width="{w:.2f}" height="33" fill="{esc(colors[name])}"/>');x+=w
 for i,(name,byt) in enumerate(sorted_lang):
  col=i%3;row=i//3;px=66+col*352;py=211+row*52
  svg.append(f'<circle cx="{px}" cy="{py-6}" r="9" fill="{esc(colors[name])}"/>')
  svg.append(line(f'{name} · {byt/total*100:.1f}%',px+20,py,21,WHITE,400,'start'))
else:svg.append(line('No language data from public owned non-fork repositories',550,190,21,MUTED))
svg.append(line(f'Percentages use GitHub-reported bytes  ·  {updated}',1040,311,14,MUTED,400,'end'))
svg.append('</svg>')
(OUT/'stats-languages.svg').write_text(''.join(svg),encoding='utf8')
print('Generated profile stats from GitHub:',cal['totalContributions'],'contributions;',len(language_counts),'languages')
