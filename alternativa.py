import sys
import KSR as KSR


user_states = {}


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
    def _init_(self):
        KSR.info('===== kamailio._init_\n')

    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0
    
    def set_state(self, user, state):
        user_states[user] = state
        name = {0: "Registed", 1: "Call", 2: "Conference"}.get(state, "Unkwon")
        KSR.info(f"State {user}: {name} ({state})\n")
    
    def get_state(self, user):
        return user_states.get(user, 0)

    def remove_user_state(self, user):
        if user in user_states:
            del user_states[user]
            KSR.info(f"State {user} removed\n")

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
                set_state(KSR.pv.get("$tu"), 0)
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
            
            # Conference call
            if "sip:conferencia@acme.pt" in KSR.pv.get("$tu"):
                KSR.pv.sets("$ru", "sip:conferencia@127.0.0.1:5090")
                KSR.info("Calling to conference. Forwarding call to: " + KSR.pv.get("$ru") + "\n")
                self.set_state(KSR.pv.get("$fu"), 2)
                KSR.tm.t_relay()

            # Check if the target user is registered
            if KSR.registrar.lookup("location") == 1:
                KSR.info("User registered. Forwarding call to: " + KSR.pv.get("$ru") + "\n")
                
                if self.get_state(KSR.pv.get("$tu")) == 1:
                    KSR.info(KSR.pv.get("$ru") + " is on a call. \n")
                    KSR.pv.sets("$ru", "sip:busyann@127.0.0.1:5080")
                    KSR.info("Calling to announcement server. Forwarding call to: " + KSR.pv.get("$ru") + "\n")
                    KSR.forward() 
                    KSR.tm.t_relay()
                    return 1

                
                if self.get_state(KSR.pv.get("$tu")) == 2:
                    KSR.info(KSR.pv.get("$ru") + " is on a Conference.\n")
                    KSR.pv.sets("$ru", "sip:inconference@127.0.0.1:5080")
                    KSR.info("Calling to announcement server. Forwarding call to: " + KSR.pv.get("$ru") + "\n")
                    KSR.forward() 
                    KSR.tm.t_relay()
                    return 1
                self.set_state(KSR.pv.get("$fu"), 1)
                self.set_state(KSR.pv.get("$tu"), 1)
                KSR.tm.t_relay()  # Forward the call
            else:
                KSR.info("User not registered: " + KSR.pv.get("$tu") + "\n")
                KSR.sl.send_reply(404, "User Not Registered")
            return 1

        # Handle BYE (DEREGISTER or call termination)
        if (msg.Method == "BYE"):
            KSR.info("BYE R-URI: " + KSR.pv.get("$ru") + "\n")
            self.set_state(KSR.pv.get("$tu"), 0)
            self.set_state(KSR.pv.get("$ru"), 0)
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