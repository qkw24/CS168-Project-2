from BasicTest import *

class DropStartAckTest(BasicTest):
	count=0
	def handle_packet(self):
		for p in self.forwarder.in_queue:
			if (p.msg_type == "ack" and p.seqno == 1):
				self.count+=1
			if not (p.msg_type == "ack" and p.seqno == 1 and self.count<5):
				self.forwarder.out_queue.append(p)
		self.forwarder.in_queue=[]
				
