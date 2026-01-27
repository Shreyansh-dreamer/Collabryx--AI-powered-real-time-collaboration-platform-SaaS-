import { forwardRef } from "react";
import GitHubIcon from '@mui/icons-material/GitHub';
import LinkedInIcon from '@mui/icons-material/LinkedIn';
import EmailIcon from '@mui/icons-material/Email';

const Footer = forwardRef((props, ref) => {
  return (
    <footer
      ref={ref}
      className="bg-gray-300 dark:bg-[#192231] text-black dark:text-white py-4"
    >
      <div className="max-w-4xl mx-auto px-4 text-center space-y-4">
        <h2 className="text-lg font-semibold">Built by Shreyansh Mishra</h2>
        <p className="text-sm">
          This is a B2B SaaS project where companies , and individuals can collaborate
          <br />
          and work, includes an agentic chatbot, rag, real time code-editor,group-chat
          <br/>
          video-calling,etc. 
        </p>

        {/* Icons with labels below */}
        <div className="flex justify-center space-x-10 font-semibold text-blue-600">
          <a
            href="https://github.com/Shreyansh-dreamer"
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col items-center"
          >
            <GitHubIcon/>
            <span>GitHub</span>
          </a>
          <a
            href="https://linkedin.com/in/shreyansh-m-69962432a"
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col items-center"
          >
            <LinkedInIcon/>
            <span>LinkedIn</span>
          </a>
          <a
            href="mailto:garenafreefiresaving@gmail.com"
            className="flex flex-col items-center"
          >
            <EmailIcon/>
            <span>Gmail</span>
          </a>
        </div>

        <p className="text-xs text-gray-400">
          &copy; {new Date().getFullYear()} All rights reserved.
        </p>
      </div>
    </footer>
  );
});

export default Footer;