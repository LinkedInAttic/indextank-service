from xml.dom.minidom import Document, parseString
import httplib
import urlparse


class AuthorizeNet:
    """
    Basic client for Authorize.net's Automated Recurring Billing (ARB) service
    """
    
    def __init__(self):
        from django.conf import settings
        f = open("authorize.settings.prod") if not settings.DEBUG else open("authorize.settings.debug")
        for line in f:
            line = line.strip()
            if len(line) > 0 and not line.startswith('#'):
                parts = line.split('=',1)
                var = parts[0].strip()
                val = parts[1].strip()
                if var in ['host_url','api_login_id','transaction_key']:
                    cmd = 'self.%s = %s' % (var,val)
                    exec(cmd)
    
    def subscription_create(self, refId, name, length, unit, startDate, totalOccurrences, trialOccurrences, 
                            amount, trialAmount, cardNumber, expirationDate, firstName, lastName, company, 
                            address, city, state, zip, country):
        doc,root = self._new_doc("ARBCreateSubscriptionRequest")
        self._add_text_node(doc, root, 'refId', refId)
        subscription = self._add_node(doc, root, 'subscription')
        self._add_text_node(doc, subscription, 'name', name)
        paymentSchedule = self._add_node(doc, subscription, 'paymentSchedule')
        interval = self._add_node(doc, paymentSchedule, 'interval')
        self._add_text_node(doc, interval, 'length', length)
        self._add_text_node(doc, interval, 'unit', unit)
        self._add_text_node(doc, paymentSchedule, 'startDate', startDate)
        self._add_text_node(doc, paymentSchedule, 'totalOccurrences', totalOccurrences)
        self._add_text_node(doc, paymentSchedule, 'trialOccurrences', trialOccurrences)
        self._add_text_node(doc, subscription, 'amount', amount)
        self._add_text_node(doc, subscription, 'trialAmount', trialAmount)
        payment = self._add_node(doc, subscription, 'payment')
        creditcard = self._add_node(doc, payment, 'creditCard')
        self._add_text_node(doc, creditcard, 'cardNumber', cardNumber)
        self._add_text_node(doc, creditcard, 'expirationDate', expirationDate)
        billto = self._add_node(doc, subscription, 'billTo')
        self._add_text_node(doc, billto, 'firstName', firstName)
        self._add_text_node(doc, billto, 'lastName', lastName)
        self._add_text_node(doc, billto, 'company', company)
        self._add_text_node(doc, billto, 'address', address)
        self._add_text_node(doc, billto, 'city', city)
        self._add_text_node(doc, billto, 'state', state)
        self._add_text_node(doc, billto, 'zip', zip)
        self._add_text_node(doc, billto, 'country', country)
        res = self._send_xml(doc.toxml())
        subscriptionId = res.getElementsByTagName('subscriptionId')[0].childNodes[0].nodeValue
        return subscriptionId
    

    def subscription_update(self, refId, subscriptionId, name, startDate, totalOccurrences, trialOccurrences, 
                            amount, trialAmount, cardNumber, expirationDate, firstName, lastName, company,
                            address, city, state, zip, country):
        doc,root = self._new_doc("ARBUpdateSubscriptionRequest")
        self._add_text_node(doc, root, 'refId', refId)
        self._add_text_node(doc, root, 'subscriptionId', subscriptionId)
        subscription = self._add_node(doc, root, 'subscription')
        if name:
            self._add_text_node(doc, subscription, 'name', name)
        if startDate or totalOccurrences or trialOccurrences:
            paymentSchedule = self._add_node(doc, subscription, 'paymentSchedule')
            if startDate:
                self._add_text_node(doc, paymentSchedule, 'startDate', startDate)
            if totalOccurrences:
                self._add_text_node(doc, paymentSchedule, 'totalOccurrences', totalOccurrences)
            if trialOccurrences:
                self._add_text_node(doc, paymentSchedule, 'trialOccurrences', trialOccurrences)
        if amount:
            self._add_text_node(doc, subscription, 'amount', amount)
        if trialAmount:
            self._add_text_node(doc, subscription, 'trialAmount', trialAmount)
        if cardNumber and expirationDate:
            payment = self._add_node(doc, subscription, 'payment')
            creditcard = self._add_node(doc, payment, 'creditCard')
            self._add_text_node(doc, creditcard, 'cardNumber', cardNumber)
            self._add_text_node(doc, creditcard, 'expirationDate', expirationDate)
        if firstName and lastName:
            billto = self._add_node(doc, subscription, 'billTo')
            self._add_text_node(doc, billto, 'firstName', firstName)
            self._add_text_node(doc, billto, 'lastName', lastName)
            if company:
                self._add_text_node(doc, billto, 'company', company)
            if address and city and state and zip and country:
                self._add_text_node(doc, billto, 'address', address)
                self._add_text_node(doc, billto, 'city', city)
                self._add_text_node(doc, billto, 'state', state)
                self._add_text_node(doc, billto, 'zip', zip)
                self._add_text_node(doc, billto, 'country', country)
        self._send_xml(doc.toxml())


    def subscription_cancel(self, refId, subscriptionId):
        doc,root = self._new_doc("ARBCancelSubscriptionRequest")
        self._add_text_node(doc, root, 'refId', refId)
        self._add_text_node(doc, root, 'subscriptionId', subscriptionId)
        self._send_xml(doc.toxml())


    def _add_node(self, doc, node, name):
        elem = doc.createElement(name)
        node.appendChild(elem)
        return elem

    def _add_text_node(self, doc, node, name, text):
        elem = self._add_node(doc, node, name)
        text_node = doc.createTextNode(text)
        elem.appendChild(text_node)
        return elem

    def _new_doc(self, operation):
        doc = Document()
        root = doc.createElement(operation)
        root.setAttribute('xmlns','AnetApi/xml/v1/schema/AnetApiSchema.xsd')
        doc.appendChild(root)
        auth = self._add_node(doc, root, 'merchantAuthentication')
        self._add_text_node(doc, auth, 'name', self.api_login_id)
        self._add_text_node(doc, auth, 'transactionKey', self.transaction_key)
        return doc, root

    def _send_xml(self, xml):
        splits = urlparse.urlsplit(self.host_url)
        print "connection.request('POST', "+self.host_url+", xml, {'Content-Type':'text/xml'})"
        print "xml: "+xml
        connection = httplib.HTTPSConnection(splits.hostname)
        connection.request('POST', self.host_url, xml, {'Content-Type':'text/xml'})
        response = connection.getresponse()
        response.body = response.read()
        connection.close()
        print "resp: "+response.body
        res = parseString(response.body)
        ok = res.getElementsByTagName('resultCode')[0].childNodes[0].nodeValue == "Ok"
        if not ok:
            code = res.getElementsByTagName('message')[0].childNodes[0].childNodes[0].nodeValue
            msg = res.getElementsByTagName('message')[0].childNodes[1].childNodes[0].nodeValue + " (%s)"%code
            raise BillingException(msg,code)
        return res


class BillingException(Exception):
    def __init__(self, msg, code):
        self.msg = msg
        self.code = code
    def __str__(self):
        return repr(self.msg)


