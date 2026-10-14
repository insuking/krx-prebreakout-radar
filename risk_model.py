"""Point-in-time price gates and separately scored chase risk. No regulatory claims."""
def risk_metrics(c,h,l):
    close=float(c.iloc[-1]); prev=float(c.iloc[-2])
    r3=close/float(c.iloc[-4])-1
    r5=close/float(c.iloc[-6])-1
    r10=close/float(c.iloc[-11])-1
    upper=(float(h.iloc[-1])-close)/max(float(h.iloc[-1]-l.iloc[-1]),1)
    high5=float(h.iloc[-5:].max())
    recent_surges=sum(float(c.iloc[-i]/c.iloc[-i-1]-1)>=.18 for i in range(1,4))
    flags=[]
    if r3>=.45 or r5>=.60 or r10>=.85:flags.append("RECENT_PARABOLIC_RISE")
    if recent_surges>=2:flags.append("MULTIPLE_RECENT_SURGES")
    if upper>=.60 and float(h.iloc[-1])/prev-1>=.12:flags.append("UPPER_WICK_REVERSAL")
    if close/high5-1<=-.18 and r5>=.25:flags.append("POST_RALLY_DRAWDOWN")
    score=min(100,round(max(0,r3)*55+max(0,r5)*35+max(0,r10)*15+upper*25+(20 if recent_surges>=2 else 0),1))
    return {"risk_score":score,"risk_flags":flags,"return_3d_pct":round(r3*100,2),"return_5d_pct":round(r5*100,2),"return_10d_pct":round(r10*100,2),"upper_wick_ratio":round(upper,3)}
