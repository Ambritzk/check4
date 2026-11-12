import pandas as pd
import matplotlib.pyplot as plt
import sys
from typing import List

class ping:
     def __init__(self,rtt,seq,timestamp):
          self.rtt = rtt
          self.seq = seq
          self.timestmp = timestamp

     def __str__(self):
          return f"({self.timestmp},{self.seq},{self.rtt})"

class stats:
    def __init__(self, mnrtt, mxrtt, loss, passed, total,maxp,maxf):
        self.mnrtt = mnrtt
        self.mxrtt = mxrtt
        self.loss = loss
        self.psd = passed
        self.total = total
        self.maxp = maxp
        self.maxf = maxf

    def __str__(self):
        return (
            f"Stats:\n"
            f"Minimum RTT = {self.mnrtt} ms\n"
            f"Maximum RTT = {self.mxrtt} ms\n"
            f"Packet Loss = {self.loss}\n"
            f"Passed = {self.psd}\n"
            f"Total = {self.total}\n"
            f"Maximum consecutive pings = {self.maxp}\n"
            f"Maximum consecutive loss = {self.maxf}\n"
        )
def parse(fname):


     with open(fname,"r") as file:
          lineno = 1
          pings = []

          for line in file:
               if lineno == 1:
                    lineno += 1
                    continue


               line = line.strip()

               tokens = line.split(" ")
               seq_tokens = tokens[5].split("=")

               seq_int = None               
               if seq_tokens[0] == "icmp_seq":
                    seq_int = int(seq_tokens[1])
               else:
                    print('Something went wrong at line',lineno)
                    return

               try:
                    time = float(tokens[-2].split("=")[-1])
               except Exception as e:
                    print(f"An exception occurred on line {lineno}.\n{e}")
                    return
               timestamp = float(tokens[0].strip("[]"))

               curr_ping = ping(time,seq_int,timestamp)
               pings.append(curr_ping)
               
               #update variables here
               lineno += 1
     return pings if len(pings) > 0 else None
               
def calculate_stats(pings:List[ping]):
     sorted_by_seq = sorted(pings,key = lambda ping: ping.seq)
     last_seen_seq = None
     pstreak = 0
     fstreak = 0
     maxp = 0
     maxf = 0
     loss = 0
     passed = len(pings)

     answer_map = []
     for p in sorted_by_seq:
          if last_seen_seq is None:
               last_seen_seq = p.seq
               continue
          if p.seq == last_seen_seq + 1:
               answer_map.append(True)
               fstreak = 0
               pstreak += 1
               if pstreak > maxp:
                    maxp = pstreak
          else:
               pstreak = 0
               diff = p.seq - last_seen_seq
               loss += (diff - 1)
               fstreak += (diff - 1)
               answer_map += [False for _ in range(diff-1)]
               if fstreak > maxf:
                    maxf = fstreak

          last_seen_seq = p.seq

     minrtt = min(pings,key=lambda p: p.rtt).rtt
     maxrtt = max(pings,key=lambda p: p.rtt).rtt
     fstats = stats(minrtt,maxrtt,loss,passed,loss+passed,maxp,maxf)
     return fstats,answer_map

def drawRTT(fname,RTT):

     RTT["datetime_utc"] = pd.to_datetime(RTT["timestamps"], unit="s", utc=True)

     #Add 5 hours for Pakistan time (UTC+5)
     RTT["datetime_pkt"] = RTT["datetime_utc"] + pd.Timedelta(hours=5)
     fig, ax = plt.subplots(figsize=(20, 10))
     ax.plot(RTT["datetime_pkt"], RTT["time"], marker="o", linestyle="-", markersize=3)

     # Add labels and a title
     ax.set_xlabel("Time (PKT)")
     ax.set_ylabel("RTT (ms)")
     ax.set_title("Ping Results Over Time")

     # Automatically rotate and format the date/time labels on the x-axis so they don't overlap
     fig.autofmt_xdate()

     # Show the plot
     plt.grid(True)
     fig.savefig(f"rttplot-{fname}.png", dpi=300, transparent=False, bbox_inches="tight")

def drawCDF(fname,RTT):
     listo = list(RTT["time"])
     listo = sorted(listo)
     ind = 0
     result = []
     sumd = 0
     unique = []
     while ind < len(listo):
          curr = listo[ind]
          count = 1
          ind += 1
          while ind < len(listo) and listo[ind] == curr:
               count += 1
               ind += 1
          sumd += count
          result.append(sumd / float(len(listo)))
          unique.append(curr)




     fig, ax = plt.subplots(figsize=(10,5))
     ax.plot(unique,result, marker="o", linestyle="-", markersize=3)

     # Add labels and a title
     ax.set_xlabel("Time (RTT)")
     ax.set_ylabel("Proportion")
     ax.set_title("Ping Results Over Time")

     fig.savefig(f"p2-{fname}.png", dpi=300, transparent=False, bbox_inches="tight")

def drawProbs(fname,answer_map):
     answer_prob = []
     loss_prob = []
     ks = list(range(-10, 11))

     for k in ks:
          answered_total = 0
          failed_total = 0
          answered_both = 0
          failed_both = 0

          for i in range(len(answer_map)):
               j = i + k

               if j < 0 or j >= len(answer_map):
                    continue

               if answer_map[i]:
                    answered_total += 1
                    if answer_map[j]:  
                         answered_both += 1
               else:
                    failed_total += 1 
                    if not answer_map[j]:
                         failed_both += 1

          answer_prob.append(answered_both / answered_total if answered_total else float("nan"))
          loss_prob.append(failed_both / failed_total if failed_total else float("nan"))

     delivery_rate = sum(answer_map) / len(answer_map)
     failed_rate = 1 - delivery_rate

     print(f"Delivery rate = {delivery_rate}\n Failure rate = {failed_rate}")

     # --- Side-by-Side Plotting ---
     fig, axes = plt.subplots(1, 2, figsize=(14, 5))

     # 1. Answer Probability Plot
     axes[0].bar(ks, answer_prob, color="skyblue", edgecolor="black")
     axes[0].axhline(delivery_rate, color="red", linestyle="--", label="Unconditional delivery rate")
     axes[0].set_xlabel("Offset k")
     axes[0].set_ylabel("P(answered at N+k | answered at N)")
     axes[0].set_title("Answer Probability")
     axes[0].set_xticks(ks)
     axes[0].set_ylim(0, 1)
     axes[0].legend()

     # 2. Loss Probability Plot
     axes[1].bar(ks, loss_prob, color="salmon", edgecolor="black")
     axes[1].axhline(failed_rate, color="blue", linestyle="--", label="Unconditional failure rate")
     axes[1].set_xlabel("Offset k")
     axes[1].set_ylabel("P(failed at N+k | failed at N)")
     axes[1].set_title("Loss Probability")
     axes[1].set_xticks(ks)
     axes[1].set_ylim(0, 1)
     axes[1].legend()

     # Adjust layout, save to file, and close figure
     plt.tight_layout()
     plt.savefig(f"probabilities_comparison-{fname}.png", dpi=300, bbox_inches="tight")
     plt.close()

def drawScatter(fname,RTT):
     fig, ax = plt.subplots(figsize=(7,7))
     x_pings = list(RTT['time'])
     y_pings = [x_pings[i + 1] for i in range(len(x_pings) - 1)]
     x_pings.pop()

     ax.scatter(x_pings,y_pings,color="royalblue",marker="o")
     ax.set_xlabel("Pings at N (RTT)")
     ax.set_ylabel("Pings at N + 1 (RTT)")
     ax.set_title("Ping N against ping N + 1")
     fig.savefig(f"scatter-{fname}.png",dpi=300,transparent=False,bbox_inches="tight")

if __name__=="__main__":
     if len(sys.argv) != 2:
          print("Expected a file name, and only one argument")
          exit(0)

     fname = sys.argv[1]
     pings = parse(fname)
     if pings is None:
          print("Pings is empty")
          exit(0)

     RTT = pd.DataFrame(columns=["timestamps","time"])
     rind = 0
     ping_n = []



     for p in pings:
          RTT.loc[rind] = [p.timestmp,p.rtt]
          rind += 1
     b = RTT
     
     for _,i in b['time'].items():
          ping_n.append(i)
     with open("pingn.txt","w") as file:
          for i in range(len(ping_n) - 1):
               file.write(f"{ping_n[i]},{ping_n[i + 1]}\n")

     stats,answer_map = calculate_stats(pings)
     drawRTT(fname,RTT)
     drawCDF(fname,RTT)
     drawProbs(fname,answer_map)
     drawScatter(fname,RTT)
     print(f"Data for {fname}:")
     print(stats)