1. Introduction  
     The Automated Jewellery Rate Notification System is a Python-based project developed to automatically send daily jewellery rates to customers on WhatsApp. In many jewellery shops, the owner checks the gold rate manually from a website and then sends the updated rate to customers or WhatsApp groups. This process takes time and can cause mistakes.  
     In this project, we created a system that automatically fetches the live rate from a website, adds a shop margin using the plus (+) method, and sends the final rate to a selected WhatsApp group. We also developed a simple front-end interface where the user can enter the group ID, set a schedule time, add margin value, and then start the automation process.  
     This system reduces manual effort and makes communication faster and more accurate.  
2. Objective  
  
    -To automatically fetch live jewellery rates from a website  
    -To add custom shop margin using plus (+) calculation  
    -To send updated rate automatically to WhatsApp group  -To create a simple front-end for easy user input -To create a simple front-end for easy user input.  
    Its primary objective include:   
  
1.	Why We Chose This Subject  
    -We selected this project because many jewellery shops still update rates manually. It is time-consuming and repetitive work. We wanted to solve a real business problem using automation and Python. This project also helps us understand web scraping, automation tools, and front-end integration in a practical way.
  
3.	Benefits of This System      
  -	Saves daily manual work  
  -	Reduces human error  
  -	Allows custom margin addition  
  -	Sends accurate rate every time  
  -	Supports scheduled automation  
  -	Easy to use because of front-end interface  

3. Proposed work  
  -The main purpose of this project is to automate the complete process of checking jewellery rates and sending them to customers  
  
  Working Process:  
    -	User opens the front-end system.  
    -	User enters WhatsApp group ID.  
    -	User sets schedule time.  
    -	User enters margin value (for example +800).  
    -	User clicks on “Start Automation”.  
    -	System opens the website and fetches live rate.  
    -	System adds margin to the original rate.  
    -	Final rate message is prepared.  
    -	WhatsApp Web opens automatically.  
    -	Message is sent to the selected group.  
  
The process runs automatically without manual work.  
  
4. Technology Details
  Frontend: Html, CSS  
  Middleware : Python (Flask)  
  Backend: Python (Webdriver manager, Selenium webdriver, PyWhatKit )  
  We are designing an Website for automation of whatsapp(rate update)

5. How to Use
   1. Set Schedule

        <img width="774" height="320" alt="image" src="https://github.com/user-attachments/assets/bf2a9ab6-0cc2-42ed-8485-9f8fbda37319" />
      
   3. Set Gold Silver Margins and add Group id

        <img width="752" height="328" alt="image" src="https://github.com/user-attachments/assets/398c6f9d-9a65-47c6-bbc6-860ba04da45f" />
      
   5. In live console its show the process

      <img width="750" height="368" alt="image" src="https://github.com/user-attachments/assets/431351ed-4e8a-440a-a475-9911a7435484" />

   
6. App UI


   <img width="706" height="957" alt="image" src="https://github.com/user-attachments/assets/a8ae1cb2-8004-47a9-a775-21c5e38f2087" />

  
   

       
  
