import logging
from typing import Optional, Union, Any, List, Dict, Callable
import json

import httpx

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ReinventHelper(object):
    host = 'catalog.awsevents.com'
    path = {'search': 'api/search'}
    attr_map = dict(
        sessiontypes={
            'Keynote': 'sessionType_keynote',
            'Innovation Talks': '1714000626207001Ycfu',
            'Bootcamp': '1707427142680004EyYF',
            'Breakout session': 'sessionType_breakoutSession',
            'Builders\' Fair': '1714000626207003YEyA',
            'Builders\' session': '1714000626207004Ym6b',
            'Chalk talk': '1707427142680006ExBa',
            'Code talk': '1707427142680007EpPU',
            'Community activities': '1714000626207007YWLW',
            'Conference services': '1714000626207008Yok3',
            'Dev chat': '1707427142680008EiAj',
            'Exam Prep': '1722368262538001acBF',
            'Gamified learning': '1707427142680015Eb45',
            'Interactive training': '1724785930869001qZpD',
            'Lightning talk': '1707427142681002Eid4',
            'Self-paced training': '1727195193103001jeql',
            'Workshop': '1707427142681004EMmw',
        },
        topic={
            'AI / ML': '1707430256139001EhRR',
            'Analytics': '1707430256139002EdEe',
            'Architecture': '1707430256139003EfiL',
            'Business Application': '1707430256139004E8Hc',
            'Cloud Operation': '1707430256139005EF97',
            'Compute': '1707430256139006Eev2',
            'Content Delivery': '1714148249632008q9IH',
            'Customer Enablement': '1707430256139007Ehur',
            'Databases': '1707430256139008EYIj',
            'Devops and Developer productivity': '1714148249632010qMQC',
            'End-user Computing': '1707430256139010EMDZ',
            'Hybrid Cloud': '1707430256139012E0Qh',
            'Internet of Things': '1707430256139013EkEY',
            'Kubernetes': '1707430256139014EYNS',
            'Migration and Modernization': '1714148249632012qGEs',
            'Networking': '1714148249632016q6QT',
            'New to AWS': '1707430256139016EvxL',
            'Security Compliance Identity': '1707430256139018E2En',
            'Serverless Computing and Container': '1714148249632020q301',
            'Storage': '1707430256139020E5Ci',
            'Training and Certification': '1707430256139021EqJi'
        },
        areaofinterest={
            'Amazon': '1714148758453005yjnl',
            'Application Integration': '1714148758453002yEqO',
            'Application Security': '1714148758453003yF0H',
            'AWS Marketplace': '1714148758453008ycbO',
            'AWS Partners': '1714148758453007yBYs',
            'Blockchain': '1714148758453009ysfc',
            'Business Intelligence': '1714148758453012yzCz',
            'Buy with Prime': '1714148758453011ya66',
            'Cost Optimization': '1715645073005001vYdX',
            'Customer Stories': '1714148758453013yH1I',
            'Data Protection': '1714148758453014y4ei',
            'DeepRacer': '1714148758453015ypu1',
            'Developer Community': '1716502206971001giay',
            'Digital Native Business (DNB)': '1714148758453016yfwk',
            'Digital Sovereignty': '1714148758453017yrtX',
            'Disaster Response and Recovery': '1714148758453018y5lN',
            'Edge Computing': '1714148758453019yGxw',
            'Event-Driven Architecture': '1714148758453020ymYM',
            'Front-End Web and Mobile': '1714148758453021yZYG',
            'Generative AI': '1714148758453023yEKe',
            'Global Infrastructure': '1714148758453022yceC',
            'Governance Risk and Compliance': '1721344684083001r4VF',
            'Inclusion and Diversity': '1714148758453024y2e3',
            'Independent Software Vendor (ISV)': '1714148758453025yNNs',
            'Innovation and Transformation': '1722014068466001enAu',
            'Lambda-Based Applications': '1714148758453029yGSP',
            'Management and Governance': '1714148758453027ycyS',
            'Microsoft .NET': '1714148758453028yn07',
            'Modernization': '1714148758453031yOWg',
            'Monitoring and Observability': '1714148758453032yVC6',
            'Multicloud': '1716502206972002gLU2',
            'Network and Infrastructure Security': '1714148758453033y9oI',
            'Non-English': '1714148758453034ylQw',
            'Open Data': '1714148758453037yREH',
            'Open Source': '1714148758453036yX2K',
            'Oracle': '1714148758453038yN0d',
            'Partner Enablement': '1721344684083002rK5K',
            'Professional Services': '1725560248305001m8WW',
            'Public Sector': '1716580755612001caxx',
            'Quantum Technologies': '1714148758453039yZte',
            'Resilience': '1714148758453040ySoR',
            'Responsible AI': '1714148758453041yvBI',
            'Robotics': '1714148758453042yT5L',
            'SaaS': '1714148758453043ychx',
            'SAP': '1714148758453044yTRg',
            'Small &amp; Midsize Business (SMB)': '1714148758453045yKJr',
            'Startup': '1714148758453048yooa',
            'Sustainability': '1714148758453049yJ80',
            'Tech for Impact': '1722448740704001VkSG',
            'Threat Detection &amp; Incident Response': '1714148758453050yi1S',
            'VMware': '1714148758453051yDax',
            'Well-Architected Framework': '1714148758453052yGiY',
            'Workforce Development': '1714148758453054yG16',
        },
        level={
            '100 - Foundational': 'option_1597340253500',
            '200 - Intermediate': 'option_1597340257085',
            '300 - Advanced': 'option_1597340262463',
            '400 - Expert': '1714149581063001gPT1',
        },
        venue={
            'Mandalay Bay': '1714149514282003u0NO',
            'Caesars Forum': '1714149514282001ui9z',
            'MGM Grand': '1714149514282004uw2u',
            'Venetian': '1714149514282006uDYu',
            'Wynn': '1714149514282007uKju',
        },
        role={
            'Academic / Researcher': '1714149736905001gFNE',
            'Advisor / Consultant': '1714149736905002gSkz',
            'Business Executive': '1714149736905003g8Gf',
            'Cloud Security Specialist': '1714149736905004gITM',
            'Data Engineer': '1714149736905005gchd',
            'Data Scientist': '1714149736905006grQs',
            'Developer / Engineer': '1714149736905007g1Yn',
            'DevOps Engineer': '1714149736905008gN0m',
            'Entrepreneur (Founder/Co-Founder)': '1714149736905009gRK8',
            'IT Administrator': '1714149736905010g39x',
            'IT Executive': '1714149736905011g1CH',
            'IT Professional / Technical Manager': '1714149736905012g3eq',
            'Press / Media Analyst': '1714149736905013gQ0Y',
            'Sales / Marketing': '1714149736905014gh9K',
            'Solution / Systems Architect': '1714149736905015gtHw',
            'Student': '1714149736905016gBFz',
            'System Administrator': '1714149736905017gyfN',
            'Tech Explorer': '1714149736905018gzAg',
            'Venture Capitalist': '1714149736905019gq1n'
        }
    )

    def __init__(
            self,
            api_profile: str
    ):

        self.api_profile = api_profile

    def _build_filter(
        self,
        sessiontypes: List[str] = [],
        topic: List[str] = [],
        industry: List[str] = [],
        areaofinterest: List[str] = [],
        level: List[str] = [],
        role: List[str] = [],
        day: List[str] = [],  # YYYYMMDD
        datehour: List[str] = [],  # YYYYMMDDtHH
        venue: List[str] = [],
    ):
        '''
        Convert filter values into AWS api attribute code
        Any invalid values are ignored
        '''
        filters = {
            'search.sessiontypes': [self.attr_map['sessiontypes'][a] for a in sessiontypes if a in self.attr_map['sessiontypes']],
            'search.topic': [self.attr_map['topic'][a] for a in topic if a in self.attr_map['topic']],
            'search.industry': [self.attr_map['industry'][a] for a in industry if a in self.attr_map['industry']],
            'search.areaofinterest': [self.attr_map['areaofinterest'][a] for a in areaofinterest if a in self.attr_map['areaofinterest']],
            'search.level': [self.attr_map['level'][a] for a in level if a in self.attr_map['level']],
            'search.role': [self.attr_map['role'][a] for a in role if a in self.attr_map['role']],
            'search.day': day,
            'search.datetime': datehour,
            'search.venue': [self.attr_map['venue'][a] for a in venue if a in self.attr_map['venue']],
        }
        for k in list(filters):
            if len(filters[k]) == 0:
                filters.pop(k)
            elif len(filters[k]) == 1:
                filters[k] = filters[k][0]
        logger.info(filters)
        return filters

    def _format_sessions(self, raw_sessions):
        '''
        Take in a list of session data from AWS response, extract needed info
        Args:
            raw_sessions: a list of raw data from aws for each session
        Retrun
            A list of extracted info for each session
        '''
        additonal_attrs = ['Topic', 'Areaofinterest',
                           'Level', 'Role', 'Walkuponlysession']
        reserve_required = [
            'Bootcamp', 'Breakout session', 'Innovation Talks', 'Chalk talk', 'Code talk',
            'Workshop', 'Exam Prep', 'Gamified learning', 'Interactive training',
        ]
        sessions = []
        for rs in raw_sessions:
            s = {
                'code': rs['code'],
                'title': rs['title'],
                'type': rs['type'],
                'abstract': rs['abstract'],
                'date': rs['times'][0]['date'],
                'day': rs['times'][0]['dayName'],
                'start_time': rs['times'][0]['startTimeFormatted'],
                'end_time': rs['times'][0]['startTimeFormatted'],
                'duration_minutes': rs['times'][0]['length'],
                'location': rs['times'][0]['room'],
            }
            for attr in rs['attributevalues']:
                if attr['attribute_id'] in additonal_attrs:
                    s.setdefault(attr['attribute'], []).append(attr['value'])
            if s['type'] in reserve_required and s.get('Walkuponlysession', 'NA') == 'NA':
                s['reservation_require'] = 'Yes'

            sessions.append(s)

        return sessions

    def list_filter_attributes(self):
        return list(self.attr_map.keys())

    def list_sessiontypes(self):
        return list(self.attr_map['sessiontypes'].keys())

    def list_venue(self):
        return list(self.attr_map['venue'].keys())

    def list_topic(self):
        return list(self.attr_map['topic'].keys())

    def list_level(self):
        return list(self.attr_map['level'].keys())

    def list_areaofinterest(self):
        return list(self.attr_map['areaofinterest'].keys())

    def list_role(self):
        return list(self.attr_map['role'].keys())

    def search_session(
        self,
        search_text: str,
        sessiontypes: List[str] = [],
        topic: List[str] = [],
        industry: List[str] = [],
        areaofinterest: List[str] = [],
        level: List[str] = [],
        role: List[str] = [],
        day: List[str] = [],  # YYYYMMDD
        datehour: List[str] = [],  # YYYYMMDDtHH
        venue: List[str] = [],
    ):
        headers = {
            # 'Host': self.host,
            'RfApiProfileId': self.api_profile
        }
        filters = self._build_filter(
            sessiontypes, topic, industry, areaofinterest, level, role, day, datehour, venue)
        data = {
            'type': 'session',
            'from': 0,
            'size': 50,
            'search': search_text,
        } | filters

        total_sessions = 0
        return_sessions = 0
        raw_sessions = []
        error = None
        try:
            r = httpx.post(
                f'https://{self.host}/{self.path["search"]}',
                headers=headers,
                data=data
            )
            r.raise_for_status()
            r_json = r.json()['sectionList'][0]
            total_sessions = r_json['total']
            return_sessions = r_json['numItems']
            raw_sessions = r_json['items']
            logger.info(
                f'Retrieved {return_sessions}/{total_sessions} sessions')
        except httpx.RequestError as ex:
            error = f'Error occurred while searching for sessions: {ex}'
            logger.error(error, stack_info=True, exc_info=True)
        except httpx.HTTPStatusError as ex:
            error = f'Error status code {ex.response.status_code}.'
            logger.error(error, stack_info=True, exc_info=True)
        except KeyError as ex:
            error = f'Information not found {ex}.'
            logger.error(error, stack_info=True, exc_info=True)

        if error:
            return error

        sessions = self._format_sessions(raw_sessions)
        logger.info(json.dumps(sessions, indent=2))

        return sessions
