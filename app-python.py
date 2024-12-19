import sys
import KSR as KSR

def dumpObj(obj):           # List all obj attributes and methods
    for attr in dir(obj):
        KSR.info("obj attr = %s" % attr)
        if (attr != "Status"):
            KSR.info(" type = %s\n" % type(getattr(obj, attr)))
        else:
            KSR.info("\n")
    return 1

def mod_init():
    KSR.info("===== from Python mod init\n")
    return kamailio()

class kamailio:
    def __init__(self):
        KSR.info('===== kamailio.__init__\n')

    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0

    def ksr_request_route(self, msg):
        # Handle REGISTER
        if (msg.Method == "REGISTER"):
            KSR.info("REGISTER R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("            To: " + KSR.pv.get("$tu") + " Contact: " + KSR.hdr.get("Contact") + "\n")
            
            # Reject registration if not @acme.pt
            if not KSR.pv.get("$tu").endswith("@acme.pt"):
                KSR.info("Registration rejected for non-acme.pt domain: " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(403, "Forbidden")
                return 1

            # Save registration for valid users
            if KSR.registrar.save('location', 0):
                KSR.info("Registration saved for " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(200, "OK")
            else:
                KSR.info("Registration failed for " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(500, "Internal Server Error")
            return 1

        # Handle INVITE (simple forwarding logic)
        if (msg.Method == "INVITE"):
            KSR.info("INVITE R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("        From: " + KSR.pv.get("$fu") + " To: " + KSR.pv.get("$tu") + "\n")

            # Debugging From Domain
            KSR.info("From Domain ($fd): " + KSR.pv.get("$fd") + "\n")
            
            # Reject calls from non-acme.pt domains
            if "acme.pt" not in KSR.pv.get("$fd"):
                KSR.info("Call rejected from non-acme.pt domain: " + KSR.pv.get("$fd") + "\n")
                KSR.sl.send_reply(403, "Forbidden")
                return 1
            
            # Check if the target user is registered
            if KSR.registrar.lookup("location") == 1:
                KSR.info("User registered. Forwarding call to: " + KSR.pv.get("$ru") + "\n")
                KSR.tm.t_relay()  # Forward the call
            else:
                KSR.info("User not registered: " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(404, "User Not Registered")
            return 1

        # Handle BYE (DEREGISTER or call termination)
        if (msg.Method == "BYE"):
            KSR.info("BYE R-URI: " + KSR.pv.get("$ru") + "\n")
            if KSR.registrar.remove("location", KSR.pv.get("$tu")):
                KSR.info("Deregistration successful for: " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(200, "OK")
            else:
                KSR.info("Deregistration failed for: " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(404, "Not Found")
            return 1

        # Default handling
        KSR.tm.t_relay()
        return 1

    def ksr_reply_route(self, msg):
        KSR.info("===== response - from kamailio python script\n")
        KSR.info("      Status is:"+ str(KSR.pv.get("$rs")) + "\n")
        return 1

    def ksr_onsend_route(self, msg):
        KSR.info("===== onsend route - from kamailio python script\n")
        KSR.info("      %s\n" % (msg.Type))
        return 1
