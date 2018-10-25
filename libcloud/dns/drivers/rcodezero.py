# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
RcodeZero Driver
"""
import json
import sys
import hashlib
import re

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.common.exceptions import BaseHTTPError
from libcloud.common.types import InvalidCredsError, MalformedResponseError
from libcloud.dns.base import DNSDriver, Zone, Record
from libcloud.dns.types import ZoneDoesNotExistError, ZoneAlreadyExistsError
from libcloud.dns.types import Provider, RecordType
from libcloud.utils.py3 import httplib

__all__ = [
    'RcodeZeroDriver',
]


class RcodeZeroResponse(JsonResponse):

    def success(self):
        i = int(self.status)
        return 200 <= i <= 299

    def parse_error(self):
        if self.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError(
                'Invalid API key. Check https://my.rcodezero.at/enableapi')

        try:
            body = self.parse_body()
        except MalformedResponseError:
            e = sys.exc_info()[1]
            body = '%s: %s' % (e.value, e.body)
        try:
            errors = [body['message']]
        except TypeError:
            return '%s (HTTP Code: %d)' % (body, self.status)
        except KeyError:
            pass

        return '%s (HTTP Code: %d)' % (' '.join(errors), self.status)


class RcodeZeroConnection(ConnectionKey):
    responseCls = RcodeZeroResponse

    def add_default_headers(self, headers):
        headers['Authorization'] = 'Bearer ' + self.key
        headers['Accept'] = 'application/json'
        return headers


class RcodeZeroDriver(DNSDriver):
    type = Provider.RCODEZERO
    name = 'RcodeZero'
    website = 'https://www.rcodezero.at/'
    connectionCls = RcodeZeroConnection

    RECORD_TYPE_MAP = {
        RecordType.A: 'A',
        RecordType.AAAA: 'AAAA',
        RecordType.AFSDB: 'AFSDB',
        RecordType.ALIAS: 'ALIAS',
        RecordType.CERT: 'CERT',
        RecordType.CNAME: 'CNAME',
        RecordType.DNAME: 'DNAME',
        RecordType.DNSKEY: 'DNSKEY',
        RecordType.DS: 'DS',
        RecordType.HINFO: 'HINFO',
        RecordType.KEY: 'KEY',
        RecordType.LOC: 'LOC',
        RecordType.MX: 'MX',
        RecordType.NAPTR: 'NAPTR',
        RecordType.NS: 'NS',
        RecordType.NSEC: 'NSEC',
        RecordType.OPENPGPKEY: 'OPENPGPKEY',
        RecordType.PTR: 'PTR',
        RecordType.RP: 'RP',
        RecordType.RRSIG: 'RRSIG',
        RecordType.SOA: 'SOA',
        RecordType.SPF: 'SPF',
        RecordType.SRV: 'SRV',
        RecordType.SSHFP: 'SSHFP',
        RecordType.SRV: 'SRV',
        RecordType.TLSA: 'TLSA',
        RecordType.TXT: 'TXT',
    }

    def __init__(self, key, secret=None, secure=True, host='my.rcodezero.at', port=None,
                 api_version='v1', **kwargs):
        """
        :param    key: API token to be used (required)
        :type     key: ``str``

        :param    secure: Whether to use HTTPS (default) or HTTP. 
        :type     secure: ``bool``

        :param    host: Hostname used for connections. Default: ``my.rcodezero.at``.
        :type     host: ``str``

        :param    port: Port used for connections.
        :type     port: ``int``

        :param    api_version: Specifies the API version to use. ``v1`` is currently the only i
                               valid option (and default)
        :type     api_version: ``str``

        :return: ``None``
        """

        if api_version == 'v1':
            self.api_root = '/api/v1'
        else:
            raise NotImplementedError('Unsupported API version: %s' %
                                      api_version)

        super(RcodeZeroDriver, self).__init__(key=key, secure=secure,
                                              host=host, port=port,
                                              **kwargs)

    def create_record(self, name, zone, type, data, extra=None):
        """
        Create a new record.

        :param name: name of the new record without the domain name, for example "www".
        :type  name: ``str``

        :param zone: Zone where the requested record is created.
        :type  zone: :class:`Zone`

        :param type: DNS record type (A, AAAA, ...).
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :param extra: Extra attributes: ttl and disabled 
        tpye   extra: ``dict``

        :rtype: :class:`Record`
        """
        action = '%s/zones/%s/rrsets' % (self.api_root, zone.id)

        payload = self._to_patchrequest(
            zone.id, None, name, type, data, extra, 'add')

        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='PATCH')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
                                            value=e.message)
            raise e
        return Record(id=None, name=name, data=data,
                      type=type, zone=zone, driver=self)

    def create_zone(self, domain, type=None, ttl=None, extra={}):
        """
        Create a new zone.

        :param name: Zone domain name (e.g. example.com)
        :type  name: ``str``

        :param domain: Zone type (master / slave). (required). 
        :type  domain: :class:`Zone`

        :param ttl: TTL for new records. (optional). Ignored by RcodeZEro
        :type  ttl: ``int``

        :param extra: Extra attributes (driver specific).
                      For example, specify
                      ``extra={'masters': ['193.0.2.2','2001:db8::2']}`` to set
                      the Master nameservers for a type=slave zone.
        :type extra: ``dict``

        :rtype: :class:`Zone`
        """
        action = '%s/zones' % (self.api_root)
        if type.lower() == 'slave' and (extra is None or extra.get('masters', None) is None):
            msg = 'Master IPs required for slave zones'
            raise ValueError(msg)
        payload = {'domain': domain.lower(), 'type': type.lower()}
        payload.update(extra)
        zone_id = domain + '.'
        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='POST')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith("Domain '%s' already exists" % domain):
                raise ZoneAlreadyExistsError(zone_id=zone_id, driver=self,
                                             value=e.message)
            raise e
        return Zone(id=zone_id, domain=domain, type=None, ttl=None,
                    driver=self, extra=extra)

    def update_zone(self, zone, domain, type=None, ttl=None, extra=None):
        """
        Update an existing zone.

        :param zone: Zone to update.
        :type  zone: :class:`Zone`

        :param domain: Zone domain name (e.g. example.com)
        :type  domain: ``str``

        :param type: Zone type (master / slave).
        :type  type: ``str``

        :param ttl: not supported. RcodeZero support TTLs per RRSet
        :type  ttl: ``int``

        :param extra: Extra attributes. (optional)
                      For example, specify
                      ``extra=eval('{'masters': ['193.0.2.2','2001:db8::2']}')`` to set
                      the Master nameservers for a type=slave zone.
        :type extra: ``dict``

        :rtype: :class:`Zone`
        """
        action = '%s/zones/%s' % (self.api_root, domain)
        if type.lower() == 'slave' and (extra is None or extra.get('masters', None) is None):
            msg = 'Master IPs required for slave zones'
            raise ValueError(msg)
        payload = {'domain': domain.lower(), 'type': type.lower()}
        if not extra is None:
            payload.update(extra)
        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='PUT')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith("Domain '%s' update failed" % domain):
                raise ZoneAlreadyExistsError(zone_id=zone_id, driver=self,
                                             value=e.message)
            raise e
        return Zone(id=zone.id, domain=domain, type=type, ttl=None,
                    driver=self, extra=extra)

    def delete_record(self, record):
        """
        Use this method to delete a record.

        :param record: record to delete (record object)
        :type record: `Record`

        :rtype: ``bool``
        """

        action = '%s/zones/%s/rrsets' % (self.api_root, record.zone.id)

        payload = self._to_patchrequest(
            record.zone.id, None, record.name, record.type, record.data, record.extra, 'delete')

        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='PATCH')

        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
                                            value=e.message)
            raise e

        return True

    def delete_zone(self, zone):
        """
        Deletes a zone.

        :param zone: zone to delete
        :type zone: `Zone`

        :rtype: ``bool``
        """
        action = '%s/zones/%s' % (self.api_root,
                                  zone.id)
        try:
            self.connection.request(action=action, method='DELETE')
        except BaseHTTPError:
            return False
        return True

    def get_zone(self, zone_id):
        """
        Return a Zone instance.

        :param zone_id: name of the required zone for
                        example "example.com".
        :type  zone_id: ``str``

        :rtype: :class:`Zone`
        :raises: ZoneDoesNotExistError: If no zone could be found.
        """
        action = '%s/zones/%s' % (self.api_root, zone_id)
        try:
            response = self.connection.request(action=action, method='GET')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.NOT_FOUND:
                raise ZoneDoesNotExistError(zone_id=zone_id, driver=self,
                                            value=e.message)
            print e.code
            raise e

        print(response.object)
        return self._to_zone(response.object)

    def list_records(self, zone):
        """
        Return a list of all records for the provided zone.

        :param zone: Zone to list records for.
        :type zone: :class:`Zone`

        :return: ``list`` of :class:`Record`
        """
        action = '%s/zones/%s/rrsets?page_size=-1' % (self.api_root, zone.id)
        try:
            response = self.connection.request(action=action, method='GET')
        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
                                            value=e.message)
            raise e
        return self._to_records(response.object['data'], zone)

    def list_zones(self):
        """
        Return a list of zones.

        :return: ``list`` of :class:`Zone`
        """
        action = '%s/zones?page_size=-1' % (self.api_root)
        response = self.connection.request(action=action, method='GET')
        return self._to_zones(response.object['data'])

    def update_record(self, record, name, type, data, extra=None):
        """
        Update an existing record.

        :param record: Record to update.
        :type  record: :class:`Record`

        :param name: nmae of the new record, for example "www".
        :type  name: ``str``

        :param type: DNS record type (A, AAAA, ...).
        :type  type: :class:`RecordType`

        :param data: Data for the record (depends on the record type).
        :type  data: ``str``

        :param extra: Extra attributes: ttl and disabled (optional)
        :type   extra: ``dict``

        :rtype: :class:`Record`
        """

        action = '%s/zones/%s/rrsets' % (self.api_root, record.zone.id)

        payload = self._to_patchrequest(
            record.zone.id, record, name, type, data, record.extra, 'update')

        try:
            self.connection.request(action=action, data=json.dumps(payload),
                                    method='PATCH')

        except BaseHTTPError:
            e = sys.exc_info()[1]
            if e.code == httplib.UNPROCESSABLE_ENTITY and \
               e.message.startswith('Could not find domain'):
                raise ZoneDoesNotExistError(zone_id=zone.id, driver=self,
                                            value=e.message)
            raise e

        return Record(id=hashlib.md5(name + ' ' + data).hexdigest(), name=name, data=data, type=type,
                      zone=record.zone, driver=self, extra=extra)

    def _to_zone(self, item):
        extra = {}
        for e in ['dnssec_status', 'dnssec_status_detail', 'dnssec_ksk_status',
                  'dnssec_ksk_status_detail', 'dnssec_ds', 'dnssec_dnskey',
                  'dnssec_safe_to_unsign', 'dnssec', 'masters', 'serial',
                  'created', 'last_check']:
            if e in item:
                extra[e] = item[e]
        return Zone(id=item['domain'], domain=item['domain'], type=item['type'],
                    ttl=None, driver=self, extra=extra)

    def _to_zones(self, items):
        zones = []
        for item in items:
            zones.append(self._to_zone(item))
        return zones

    def _to_records(self, items, zone):
        records = []
        for item in items:
            for record in item['records']:
                extra = {}
                extra['disabled'] = record['disabled']
                # strip domain and trailing dot from recordname
                recordname = re.sub('.' + zone.id + '$', '', item['name'][:-1])
                records.append(Record(id=hashlib.md5(recordname + ' ' + record['content']).hexdigest(),
                                      name=recordname, data=record['content'],
                                      type=item['type'], zone=zone,
                                      driver=self, ttl=item['ttl'], extra=extra))
        return records

    # rcodezero supports only rrset, so we must create rrsets from the given record
    def _to_patchrequest(self, zone, record, name, type, data, extra, action):
        rrset = {}

        cur_records = self.list_records(
            Zone(id=zone, domain=None, type=None, ttl=None, driver=self))

        if name != '':
            rrset['name'] = name + '.' + zone + '.'
        else:
            rrset['name'] = zone + '.'

        rrset['type'] = type
        rrset['changetype'] = action
        rrset['records'] = []
        if not (extra is None or extra.get('ttl', None)is None):
            rrset['ttl'] = extra['ttl']

        content = {}
        if not action == 'delete':
            content['content'] = data
            if not (extra is None or extra.get('disabled', None) is None):
                content['disabled'] = extra['disabled']
            rrset['records'].append(content)

        id = hashlib.md5(name + ' ' + data).hexdigest()
    # check if rrset contains more than one record. if yes we need to create an update request
        for r in cur_records:
            if name == r.name and r.id != id:  # we have other records with the same name
                rrset['changetype'] = 'update'
                content = {}
                content['content'] = r.data
                if not (r.extra is None or r.extra.get('disabled', None) is None):
                    content['disabled'] = r.extra['disabled']
                rrset['records'].append(content)
        request = list()
        request.append(rrset)
        return request
