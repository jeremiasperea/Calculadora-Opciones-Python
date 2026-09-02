from dataclasses import dataclass
import numpy as np
from scipy.stats import norm

@dataclass
class Leg:
    option_type: str = "CALL"
    side: str = "COMPRA"
    quantity: float = 0.0
    strike: float = 1000.0
    premium: float = 0.0

    @property
    def signed_quantity(self):
        return self.quantity if self.side == "COMPRA" else -self.quantity

def payoff_leg(spot, leg):
    spot=np.asarray(spot,dtype=float)
    intrinsic=np.maximum(spot-leg.strike,0) if leg.option_type=="CALL" else np.maximum(leg.strike-spot,0)
    return leg.signed_quantity*(intrinsic-leg.premium)

def strategy_payoff(spot, legs, multiplier=1.0):
    spot=np.asarray(spot,dtype=float)
    result=np.zeros_like(spot)
    for leg in legs:
        if leg.quantity:
            result += payoff_leg(spot,leg)*multiplier
    return result

def _d1d2(S,K,T,sigma,r,q):
    S=np.asarray(S,dtype=float)
    T=np.maximum(np.asarray(T,dtype=float),1e-12)
    sigma=np.maximum(np.asarray(sigma,dtype=float),1e-12)
    d1=(np.log(S/K)+(r-q+0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    return d1,d1-sigma*np.sqrt(T)

def bsm(S,K,T_days,sigma,r=0,q=0,option_type="CALL"):
    T=np.asarray(T_days,dtype=float)/365
    d1,d2=_d1d2(S,K,T,sigma,r,q)
    er=np.exp(-r*T); eq=np.exp(-q*T)
    if option_type=="CALL":
        return S*eq*norm.cdf(d1)-K*er*norm.cdf(d2)
    return K*er*norm.cdf(-d2)-S*eq*norm.cdf(-d1)

def greeks(S,K,T_days,sigma,r=0,q=0,option_type="CALL"):
    T=max(float(T_days)/365,1e-12)
    d1,d2=_d1d2(S,K,T,sigma,r,q)
    eq=np.exp(-q*T); er=np.exp(-r*T); sq=np.sqrt(T); pdf=norm.pdf(d1)
    if option_type=="CALL":
        delta=eq*norm.cdf(d1)
        theta=(-(S*eq*pdf*sigma)/(2*sq)-r*K*er*norm.cdf(d2)+q*S*eq*norm.cdf(d1))/365
        rho=K*T*er*norm.cdf(d2)/100
    else:
        delta=eq*(norm.cdf(d1)-1)
        theta=(-(S*eq*pdf*sigma)/(2*sq)+r*K*er*norm.cdf(-d2)-q*S*eq*norm.cdf(-d1))/365
        rho=-K*T*er*norm.cdf(-d2)/100
    return {
        "value":float(bsm(S,K,T_days,sigma,r,q,option_type)),
        "delta":float(delta),
        "gamma":float(eq*pdf/(S*sigma*sq)),
        "vega":float(S*eq*pdf*sq/100),
        "theta":float(theta),
        "rho":float(rho)
    }

def strategy_greeks(S,days,sigma,r,q,legs,multiplier=1):
    total={k:0.0 for k in ["value","delta","gamma","vega","theta","rho"]}
    for leg in legs:
        if not leg.quantity: continue
        g=greeks(S,leg.strike,days,sigma,r,q,leg.option_type)
        factor=leg.signed_quantity*multiplier
        for k in total: total[k]+=g[k]*factor
    return total

def approximate_breakevens(prices,pnl):
    roots=[]
    for i in range(len(prices)-1):
        y1,y2=pnl[i],pnl[i+1]
        if y1==0: roots.append(float(prices[i]))
        elif y1*y2<0:
            roots.append(float(prices[i]+(-y1)*(prices[i+1]-prices[i])/(y2-y1)))
    return roots

def probability_metrics(spot,days,sigma,r,q,legs,multiplier=1):
    if days<=0 or sigma<=0: return {"prob_profit":np.nan,"expected_pnl":np.nan}
    T=days/365
    x=np.linspace(-5,5,20001)
    z=x
    prices=spot*np.exp((r-q-0.5*sigma*sigma)*T+sigma*np.sqrt(T)*z)
    pnl=strategy_payoff(prices,legs,multiplier)
    pdf=np.exp(-0.5*z*z)/np.sqrt(2*np.pi)
    prob=np.trapezoid((pnl>0)*pdf,z)
    expected=np.trapezoid(pnl*pdf,z)
    return {"prob_profit":float(prob),"expected_pnl":float(expected)}
