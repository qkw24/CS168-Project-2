import sys
import getopt

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        # if sackMode:
        #     raise NotImplementedError #remove this line when you implement SACK
        self.sending_window = [] #list of dictionaries [{seq_no : packet}, ...]
        self.window_start_number = 0
        self.end_reached = False #end of data stream
        self.expected_end_ack = {} #{sequence_number : expected_ack}
        self.should_stop_transmission = False
        self.duplicate_count = 0
        self.next_msg = None
        self.cur_msg = None
        self.received = None

    # Main sending loop.

    def start(self):

        while not self.should_stop_transmission:
            if not self.end_reached:
                self.send__fill_the_window(5 - len(self.sending_window), len(self.sending_window))
            response = self.receive(0.5)
            if response and Checksum.validate_checksum(response):
                response_type, ack_num_str, data, checksum = self.split_packet(response)

                if response_type == "sack":
                    #print "SACK got!"
                    #print ack_num_str
                    ack_num = int(ack_num_str.split(';')[0])
                    self.received = ack_num_str.split(';')[1].split(',')
                else:
                    ack_num = int(ack_num_str)

                self.check_for_stop(ack_num)

                #checks for out of order acks
                #if ack_num is smaller than current window, then better ignore it, but we didn't
                if ack_num - self.window_start_number > 0:
                    self.handle_new_ack(ack_num)
                else:
                    self.handle_dup_ack(ack_num)
            else:
                self.handle_timeout(self.received)

        self.infile.close()

    def send__fill_the_window(self, allowance, occupied_capacity):
        for pos in range(0, allowance):
            if self.cur_msg is None:
                self.cur_msg = self.infile.read(1372)
                self.peek_next()
            else:
                self.cur_msg = self.next_msg
                self.peek_next()

            self.create_packet(pos, occupied_capacity)

    def peek_next(self): #peek the next data stream chunk, if next_msg is empty, that means it's the end
        self.next_msg = self.infile.read(1372)
        if self.next_msg == "":
            self.end_reached = True

    def create_packet(self, packet_position, occupied_capacity):
        msg = self.cur_msg
        seqno = self.window_start_number + occupied_capacity + packet_position

        if seqno == 0:
            msg_type = 'start'
        elif self.end_reached:
            self.expected_end_ack[seqno] = seqno + 1
            msg_type = 'end'
        else:
            msg_type = 'data'
        packet = self.make_packet(msg_type, seqno, msg)
        self.send(packet)
        self.sending_window.append({seqno : packet})

    def check_for_stop(self, ack):
        if ack in self.expected_end_ack.values():
            self.should_stop_transmission = True

    def handle_timeout(self, received=None):
        if received:
            self.send_unacked_packets()
        else:
            for p in self.sending_window:
                self.send(p.values()[0])

    def handle_new_ack(self, ack):
        items_to_remove = ack - self.window_start_number
        for i in range(0, items_to_remove):
            self.sending_window.pop(0)
        self.window_start_number = ack

    def handle_dup_ack(self, ack):
        self.duplicate_count += 1
        if self.duplicate_count >= 3:
            self.send(self.sending_window[0].values()[0])
            self.duplicate_count = 0

    def send_unacked_packets(self):
        for i in self.sending_window:
            if str(i.keys()[0]) not in self.received:
                self.send(i.values()[0])

    def log(self, msg):
        if self.debug:
            print msg


'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
